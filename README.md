# Tarea 2 — Sistemas Distribuidos 2026-1

**Autores:**
- Dante Libiot — dante.libiot@mail.udp.cl  
- Benjamín Jiménez — benjamin.jimenez4@mail.udp.cl  

**Profesor:** Nicolás Hidalgo

Evolución a una arquitectura distribuida orientada a eventos utilizando **Apache Kafka**. El sistema desacopla el generador de tráfico (cliente) de los nodos de procesamiento (workers) mediante un enfoque asíncrono, garantizando alta disponibilidad, tolerancia a fallos y semántica de entrega *At-Least-Once* frente a sobrecargas y consultas maliciosas (uso de *Dead Letter Queue* y políticas de reintento).

---

## Descripción

El sistema inyecta peticiones de forma asíncrona hacia un *message broker* (Kafka). Los nodos consumidores (*Workers*) extraen y procesan las peticiones a su propio ritmo, validando resultados contra Redis. Se evalúa el comportamiento del clúster bajo estrés, midiendo métricas dinámicas como el *Throughput*, el tamaño del *Backlog* (mensajes en espera), latencias acumuladas, y tiempos de recuperación (*Recovery Time*) al inyectar fallos controlados (*Chaos Testing*).

---

## Estructura del Proyecto

```
Tarea1_sist-dist/
├── server/
│   ├── backend/        # FastAPI — API de métricas, lee Redis y calcula Backlog/Recovery Time
│   └── frontend/       # Dashboard HTML/JS — visualización de telemetría en vivo
├── client/
│   ├── backend/        # FastAPI — Productor Kafka (inyector masivo y Poison Pills)
│   └── frontend/       # HTML/JS — interfaz para lanzar experimentos y Chaos Testing
├── worker/             # Consumidor Kafka — procesa consultas, reintentos y enruta a DLQ
├── docker-compose.yml  # Orquestador de servicios (Kafka, Zookeeper, Redis, App)
└── lab02_informe.tex   # Informe técnico y análisis de resultados
```
## Requisitos

- Docker
- Docker Compose

---

## Cómo levantar el sistema

```bash
docker-compose up --build -d
docker-compose up --build 
```

Luego abrir:
- **Panel del Servidor:** http://localhost:3000
- **Panel del Cliente:** http://localhost:3001
- **Panel de Kafka:** http://localhost:8080

---

## Escalamiento Horizontal
Para demostrar la elasticidad del sistema agregando más workers en caliente:

```bash
docker-compose up -d --scale worker=3
```
---

##Funcionamiento 
- Levantar la infraestructura y abrir Kafka UI para verificar la creación de los tópicos (queries-main, queries-retry, queries-dlq).
- Ir al Panel del Cliente (puerto 3001), seleccionar el patrón de distribución (Uniforme, Zipf o Poison Pill) y el número total de consultas.
- Iniciar el experimento.
- Ir al Panel del Servidor (puerto 3000) y observar en tiempo real la absorción de carga: formación y descenso del Backlog Size, latencias ($p50$/$p95$) y el Throughput.
- En caso de inyectar fallos (Poison Pills), monitorear cómo el sistema aísla los errores revisando el Retry Rate, DLQ Rate y el Recovery Time.

## Dataset

Google Open Buildings — tile de Chile central (~1.7M registros). El archivo `967_buildings.csv` debe estar en la raíz del proyecto antes de levantar el sistema (no se incluye en el repositorio por su tamaño).

---

## Links

- Repositorio: https://github.com/B3-njamin/Tarea1_sist-dist
- Video de demostración: (pendiente)
