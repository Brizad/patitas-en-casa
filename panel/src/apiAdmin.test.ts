import { describe, expect, it } from "vitest";
import { problemaContrasena } from "./apiAdmin";

describe("problemaContrasena (RNF-05)", () => {
  it("exige entre 12 y 128 caracteres, como el servidor", () => {
    expect(problemaContrasena("corta")).toMatch(/12/);
    expect(problemaContrasena("x".repeat(12))).toBeNull();
    expect(problemaContrasena("x".repeat(129))).toMatch(/128/);
  });
});
