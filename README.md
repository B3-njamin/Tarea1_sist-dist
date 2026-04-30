# Tarea 1 — Sistemas Distribuidos 2026-1

**Autor:** Dante Libiot — dante.libiot@mail.udp.cl  
**Profesor:** Nicolás Hidalgo

Sistema de caché distribuido con Redis para optimizar consultas geoespaciales sobre edificaciones en Santiago de Chile.

---

## Descripción

El sistema simula consultas de empresas de logística sobre zonas de Santiago. Las respuestas se guardan en Redis para evitar recalcularlas. Se evalúa el impacto de distintas políticas de evicción (LFU, LRU, FIFO), tamaños de caché (50MB, 200MB, 500MB), TTL y distribuciones de tráfico (uniforme y Zipf).

---

## Estructura del Proyecto

```
Tarea1_sist-dist/
├── server/
│   ├── backend/        # FastAPI — procesa consultas Q1-Q5, gestiona Redis y métricas
│   └── frontend/       # Dashboard HTML/JS — configuración, métricas en vivo e historial
├── client/
│   ├── backend/        # FastAPI — generador de tráfico (Zipf y uniforme)
│   └── frontend/       # HTML/JS — interfaz para lanzar experimentos
├── docker-compose.yml
└── lab01_informe.tex
```

---

## Requisitos

- Docker
- Docker Compose

---

## Cómo levantar el sistema

```bash
docker-compose up --build
```

Luego abrir:
- **Panel del Servidor:** http://localhost:3000
- **Panel del Cliente:** http://localhost:3001

---

## Flujo de uso

1. Ir al Panel del Servidor (puerto 3000) y configurar política de evicción, tamaño de memoria y TTL.
2. Ir al Panel del Cliente (puerto 3001), seleccionar distribución y número de consultas.
3. Iniciar el experimento y observar las métricas en vivo en el Panel del Servidor.
4. Al terminar, revisar el historial y los gráficos comparativos en el Panel del Servidor.

---

## Consultas implementadas

| Consulta | Descripción |
|----------|-------------|
| Q1 | Conteo de edificios por zona con filtro de confianza |
| Q2 | Área promedio y total de edificaciones |
| Q3 | Densidad de edificaciones por km² |
| Q4 | Comparación de densidad entre dos zonas |
| Q5 | Distribución del score de confianza en una zona |

---

## Dataset

Google Open Buildings — tile de Chile central (~1.7M registros). El archivo `967_buildings.csv` debe estar en la raíz del proyecto antes de levantar el sistema (no se incluye en el repositorio por su tamaño).

---

## Links

- Repositorio: https://github.com/B3-njamin/Tarea1_sist-dist
- Video de demostración: (pendiente)
