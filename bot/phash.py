"""Hash perceptual (pHash por DCT, 64 bits) con Pillow + numpy.

Detecta que dos imágenes son "la misma" aunque vengan recomprimidas,
reescaladas o con un recorte ligero, pero sin confundir imágenes distintas
que simplemente comparten un fondo plano u oscuro (que es donde un dHash
simple falla).

Método clásico: escala a 32x32 en gris, aplica DCT-II 2D, toma el bloque
8x8 de baja frecuencia (sin el término DC, que solo codifica el brillo) y
convierte a bits comparando contra la mediana.
"""
import numpy as np
from PIL import Image

N = 32      # tamaño de trabajo
K = 8       # bloque de baja frecuencia -> 64 bits

# Matriz DCT-II ortonormal, precalculada una sola vez
_k = np.arange(N)
_DCT = np.cos(np.pi * (2 * _k[None, :] + 1) * _k[:, None] / (2 * N))
_DCT[0] *= np.sqrt(1 / N)
_DCT[1:] *= np.sqrt(2 / N)


def dhash(img):
    """Nombre conservado por compatibilidad; calcula pHash."""
    return phash(img)


def phash(img):
    g = np.asarray(img.convert("L").resize((N, N), Image.LANCZOS), dtype=np.float64)
    coef = _DCT @ g @ _DCT.T
    block = coef[:K, :K].flatten()
    block = block[1:]                      # fuera el DC: no queremos juzgar por brillo
    med = np.median(block)
    bits = 0
    for v in block:
        bits = (bits << 1) | int(v > med)
    return f"{bits:016x}"


def distance(a, b):
    """Distancia de Hamming entre dos hashes hexadecimales."""
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except (ValueError, TypeError):
        return 64  # ilegible -> tratamos como totalmente distinta
