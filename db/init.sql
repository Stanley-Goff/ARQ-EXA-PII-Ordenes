SET NOCOUNT ON;
GO

IF DB_ID(N'OrdenesDB') IS NULL
    CREATE DATABASE OrdenesDB;
GO

USE OrdenesDB;
GO

IF OBJECT_ID(N'dbo.ordenes', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ordenes (
        id      INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ordenes PRIMARY KEY,
        cliente NVARCHAR(120)     NOT NULL,
        fecha   DATE              NOT NULL CONSTRAINT DF_ordenes_fecha DEFAULT (CAST(GETDATE() AS DATE)),
        estado  NVARCHAR(20)      NOT NULL CONSTRAINT DF_ordenes_estado DEFAULT (N'Pendiente'),
        total   DECIMAL(12,2)     NOT NULL CONSTRAINT DF_ordenes_total DEFAULT (0),
        CONSTRAINT CK_ordenes_estado CHECK (estado IN (N'Pendiente', N'Pagada', N'Anulada'))
    );
END
GO

IF OBJECT_ID(N'dbo.orden_detalle', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.orden_detalle (
        id              INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_orden_detalle PRIMARY KEY,
        orden_id        INT               NOT NULL,
        producto        NVARCHAR(120)     NOT NULL,
        cantidad        INT               NOT NULL CONSTRAINT CK_detalle_cantidad CHECK (cantidad > 0),
        precio_unitario DECIMAL(12,2)     NOT NULL CONSTRAINT CK_detalle_precio CHECK (precio_unitario >= 0),
        subtotal        DECIMAL(12,2)     NOT NULL,
        CONSTRAINT FK_detalle_orden FOREIGN KEY (orden_id) REFERENCES dbo.ordenes (id)
    );
    CREATE INDEX IX_detalle_orden_id ON dbo.orden_detalle (orden_id);
END
GO

-- Datos de prueba: 5 ordenes con 2 o mas lineas cada una (solo si la tabla esta vacia).
IF NOT EXISTS (SELECT 1 FROM dbo.ordenes)
BEGIN
    DECLARE @o INT;

    INSERT INTO dbo.ordenes (cliente, fecha, estado, total) VALUES (N'Ana Martinez', '2026-11-02', N'Pagada', 0);
    SET @o = SCOPE_IDENTITY();
    INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) VALUES
        (@o, N'Laptop 14 pulgadas', 1, 12500.00, 12500.00),
        (@o, N'Mouse inalambrico',  2,   350.00,   700.00);

    INSERT INTO dbo.ordenes (cliente, fecha, estado, total) VALUES (N'Carlos Pineda', '2026-11-04', N'Pendiente', 0);
    SET @o = SCOPE_IDENTITY();
    INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) VALUES
        (@o, N'Monitor 24 pulgadas', 2, 3200.00, 6400.00),
        (@o, N'Teclado mecanico',    1, 1450.00, 1450.00),
        (@o, N'Cable HDMI 2m',       3,  120.00,  360.00);

    INSERT INTO dbo.ordenes (cliente, fecha, estado, total) VALUES (N'Distribuidora La Ceiba', '2026-11-05', N'Pagada', 0);
    SET @o = SCOPE_IDENTITY();
    INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) VALUES
        (@o, N'Router WiFi 6',      5, 1800.00, 9000.00),
        (@o, N'Switch 8 puertos',   3,  950.00, 2850.00);

    INSERT INTO dbo.ordenes (cliente, fecha, estado, total) VALUES (N'Maria Fernanda Lopez', '2026-11-09', N'Anulada', 0);
    SET @o = SCOPE_IDENTITY();
    INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) VALUES
        (@o, N'Disco SSD 1TB',  2, 2100.00, 4200.00),
        (@o, N'Memoria RAM 16GB', 2, 1600.00, 3200.00);

    INSERT INTO dbo.ordenes (cliente, fecha, estado, total) VALUES (N'Tecnologias del Valle', '2026-11-12', N'Pendiente', 0);
    SET @o = SCOPE_IDENTITY();
    INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) VALUES
        (@o, N'Impresora multifuncional', 1, 4800.00, 4800.00),
        (@o, N'Toner negro',              4,  780.00, 3120.00),
        (@o, N'Resma de papel carta',    10,   95.00,  950.00);

    UPDATE o
       SET total = (SELECT COALESCE(SUM(d.subtotal), 0) FROM dbo.orden_detalle d WHERE d.orden_id = o.id)
      FROM dbo.ordenes o;
END
GO
