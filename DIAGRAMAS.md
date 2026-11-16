# Diagrama de la arquitectura

Tres contenedores (más un servicio de inicialización de un solo uso) conectados por una red bridge propia. Solo `api` se conecta a SQL Server; `web` consume la API por el nombre del servicio.

```mermaid
flowchart LR
    U["Navegador<br/>(usuario)"]

    subgraph HOST["Equipo anfitrión (Docker)"]
        direction LR
        subgraph NET["Red bridge: ordenes_net"]
            direction LR
            WEB["web<br/>Python + Django<br/>puerto 8000<br/>0.5 CPU / 256 MB"]
            API["api<br/>Python + Flask<br/>puerto 5000<br/>0.5 CPU / 256 MB"]
            DB[("db<br/>SQL Server 2022<br/>puerto 1433 (solo red interna)<br/>1 CPU / 2 GB")]
            INIT["db-init<br/>sqlcmd + init.sql<br/>(se ejecuta una vez)"]
        end
        VOL[("Volumen con nombre<br/>sqlserver_data<br/>/var/opt/mssql")]
    end

    U -- "HTTP :8000" --> WEB
    U -. "HTTP :5000 (pruebas con curl/Postman)" .-> API
    WEB -- "http://api:5000 (requests)" --> API
    API -- "db:1433 (pymssql)" --> DB
    INIT -- "db:1433 (sqlcmd)" --> DB
    DB --- VOL
```

## Orden de arranque (`depends_on` con `service_healthy`)

```mermaid
flowchart LR
    DB["db<br/>healthy"] --> INIT["db-init<br/>completed successfully"]
    DB --> API["api<br/>healthy"]
    INIT --> API
    API --> WEB["web<br/>healthy"]
```
