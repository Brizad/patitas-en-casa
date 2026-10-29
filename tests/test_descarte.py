"""D-02 (#75): descartar un reporte falso o duplicado, con justificación.

«Descartado» estaba en el ERS (R09) y no en el código. Reglas: solo el veterinario descarta
(como RN-06); la justificación sigue RN-16 y D-07; un reporte se confirma o se descarta una
sola vez; el descartado sale de la cola y el ciudadano ve «Descartado» sin el motivo (RN-14).
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import (
    EstadoReporte,
    MotivoDescarte,
    Prioridad,
    Refugio,
    Reporte,
    Rol,
    Ubicacion,
    Usuario,
)
from app.reportes.confirmacion import ReporteYaConfirmado, ServicioConfirmacion
from app.reportes.descarte import DescarteInvalido, ServicioDescarte
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

VET = Usuario("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, hash_contrasena="x")
CLAVE = "clave-de-prueba-larga"  # falsa
MOTIVO = "Ya lo reportaron hace una hora en la misma esquina"


def reporte(codigo):
    return Reporte(codigo=codigo, descripcion="Perro herido en la esquina del parque",
                   ubicacion=Ubicacion(7.89, -72.5), prioridad=Prioridad.ALTA,
                   confianza=0.7, estado=EstadoReporte.CLASIFICADO)


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    repo = (RepositorioPostgres(request.getfixturevalue("bd_limpia"))
            if request.param == "postgres" else RepositorioEnMemoria())
    repo.guardar(reporte("AAAA1111"))
    repo.guardar(reporte("BBBB2222"))
    return repo


def test_descartar_como_duplicado_queda_registrado(repositorio):
    ServicioDescarte(repositorio).descartar("BBBB2222", VET, MotivoDescarte.DUPLICADO, MOTIVO,
                                            duplicado_de="AAAA1111")
    assert repositorio.buscar("BBBB2222").estado == EstadoReporte.DESCARTADO
    descarte = repositorio.descarte("BBBB2222")
    assert (descarte.veterinario, descarte.motivo, descarte.duplicado_de, descarte.justificacion) \
        == ("vet@patitas.co", MotivoDescarte.DUPLICADO, "AAAA1111", MOTIVO)


def test_no_se_descarta_dos_veces_ni_despues_de_confirmar(repositorio):
    servicio = ServicioDescarte(repositorio)
    servicio.descartar("AAAA1111", VET, MotivoDescarte.FALSO, MOTIVO)
    with pytest.raises(ReporteYaConfirmado):
        servicio.descartar("AAAA1111", VET, MotivoDescarte.FALSO, MOTIVO)
    ServicioConfirmacion(repositorio).confirmar("BBBB2222", VET)
    with pytest.raises(ReporteYaConfirmado):
        servicio.descartar("BBBB2222", VET, MotivoDescarte.FALSO, MOTIVO)
    with pytest.raises(ReporteYaConfirmado):
        ServicioConfirmacion(repositorio).confirmar("AAAA1111", VET)


@pytest.mark.parametrize("justificacion, duplicado_de", [
    ("..........", None),          # relleno (D-07)
    ("corto", None),               # menos de 10 caracteres (RN-16)
    (MOTIVO, "BBBB2222"),          # duplicado de sí mismo
    (MOTIVO, "NOEXISTE"),          # duplicado de un reporte que no existe
])
def test_descarte_invalido_no_cambia_nada(repositorio, justificacion, duplicado_de):
    with pytest.raises(DescarteInvalido):
        ServicioDescarte(repositorio).descartar("BBBB2222", VET, MotivoDescarte.DUPLICADO,
                                                justificacion, duplicado_de=duplicado_de)
    assert repositorio.buscar("BBBB2222").estado == EstadoReporte.CLASIFICADO


def test_solo_el_veterinario_descarta():
    coord = Usuario("c@patitas.co", "Coord", Rol.COORDINADOR, hash_contrasena="x")
    repo = RepositorioEnMemoria()
    repo.guardar(reporte("AAAA1111"))
    with pytest.raises(PermissionError):
        ServicioDescarte(repo).descartar("AAAA1111", coord, MotivoDescarte.FALSO, MOTIVO)


# --- API ---------------------------------------------------------------------

def cliente():
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo="vet@patitas.co"):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_api_descartar_sale_de_la_cola_y_el_seguimiento_no_muestra_el_motivo():
    c = cliente()
    codigo = c.post("/reportes", json={"descripcion": "Gato atrapado en el techo de la casa",
                                       "direccion": "Calle 5"}).json()["codigo"]
    assert c.post(f"/reportes/{codigo}/descarte", json={"motivo": "falso"}).status_code == 401
    assert c.post(f"/reportes/{codigo}/descarte", json={"motivo": "falso", "justificacion": MOTIVO},
                  headers=sesion(c, "coord@patitas.co")).status_code == 403
    r = c.post(f"/reportes/{codigo}/descarte", json={"motivo": "falso", "justificacion": MOTIVO},
               headers=sesion(c))
    assert r.status_code == 200 and r.json() == {"codigo": codigo, "estado": "descartado"}
    assert c.get("/cola", headers=sesion(c)).json() == []
    seguimiento = c.get(f"/reportes/{codigo}/seguimiento")
    pasos = seguimiento.json()["pasos"]
    assert [p["nombre"] for p in pasos] == ["Recibido", "Descartado"]
    assert MOTIVO not in seguimiento.text and "falso" not in seguimiento.text
    repetido = c.post(f"/reportes/{codigo}/descarte",
                      json={"motivo": "falso", "justificacion": MOTIVO}, headers=sesion(c))
    assert repetido.status_code == 409


def test_api_justificacion_de_relleno_da_422():
    c = cliente()
    codigo = c.post("/reportes", json={"descripcion": "Gato atrapado en el techo de la casa",
                                       "direccion": "Calle 5"}).json()["codigo"]
    r = c.post(f"/reportes/{codigo}/descarte",
               json={"motivo": "falso", "justificacion": ".........."}, headers=sesion(c))
    assert r.status_code == 422
