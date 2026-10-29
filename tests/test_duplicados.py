"""RF-17 (#75): la cola señala posibles duplicados: a menos de 200 m y 2 horas.

Solo se señala: decidir si es duplicado es del veterinario (lo descarta con D-02).
"""
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import EstadoReporte, Prioridad, Refugio, Reporte, Rol, Ubicacion
from app.reportes.duplicados import distancia_m, posibles_duplicados
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

T0 = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
PARQUE = (7.8939, -72.5078)  # Parque Santander, Cúcuta


def reporte(codigo, lat=PARQUE[0], lon=PARQUE[1], minutos=0, direccion=None,
            estado=EstadoReporte.CLASIFICADO):
    ubicacion = Ubicacion(lat, lon) if lat is not None else Ubicacion(direccion=direccion)
    return Reporte(codigo=codigo, descripcion="Perro herido cerca del parque principal",
                   ubicacion=ubicacion, prioridad=Prioridad.ALTA, confianza=0.8,
                   estado=estado, creado_en=T0 + timedelta(minutes=minutos))


def test_distancia_entre_dos_puntos_cercanos():
    # 0,001° de latitud son unos 111 m.
    assert 105 < distancia_m(PARQUE, (PARQUE[0] + 0.001, PARQUE[1])) < 117


def test_cerca_y_en_el_mismo_rato_es_posible_duplicado():
    a, b = reporte("AAAA1111"), reporte("BBBB2222", lat=PARQUE[0] + 0.001, minutos=30)
    assert posibles_duplicados(b, [a, b]) == ["AAAA1111"]
    assert posibles_duplicados(a, [a, b]) == ["BBBB2222"]


def test_lejos_o_a_otra_hora_o_sin_gps_no_se_senala():
    base = reporte("AAAA1111")
    otros = [reporte("LEJOS001", lat=PARQUE[0] + 0.01),          # ~1,1 km
             reporte("TARDE001", minutos=121),                   # 2 h y 1 min después
             reporte("SINGPS01", lat=None, direccion="Calle 10"),
             reporte("DESCAR01", estado=EstadoReporte.DESCARTADO)]
    assert posibles_duplicados(base, [base, *otros]) == []


def test_la_cola_muestra_los_posibles_duplicados():
    repositorio = RepositorioEnMemoria()
    repositorio.guardar(reporte("AAAA1111"))
    repositorio.guardar(reporte("BBBB2222", minutos=10))
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana", Rol.VETERINARIO,
                                         "clave-de-prueba-larga")
    c = TestClient(crear_app(repositorio, RepositorioCuposEnMemoria(Refugio("Demo", 40)),
                             repositorio_usuarios=usuarios,
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-car")))
    t = c.post("/auth/token", data={"username": "vet@patitas.co",
                                     "password": "clave-de-prueba-larga"}).json()["access_token"]
    cola = c.get("/cola", headers={"Authorization": f"Bearer {t}"}).json()
    assert {r["codigo"]: r["posibles_duplicados"] for r in cola} == {
        "AAAA1111": ["BBBB2222"], "BBBB2222": ["AAAA1111"]}
