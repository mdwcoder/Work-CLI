[Español](README.es.md) | [English](README.en.md)

---

# Work-CLI

Tracker de tiempo profesional para terminal: privado, multiusuario, con IA opcional y multiplataforma.

Work-CLI combina gestion de tiempo con analisis, backups y cifrado para desarrolladores que prefieren trabajar desde la CLI.

## Caracteristicas

- Seguimiento de tiempo: iniciar, parar y pausar con descripcion.
- Informes: exportacion CSV/PDF y correo.
- Insights con IA.
- Multiusuario con cuentas aisladas.
- Privacidad con cifrado AES-256.
- Backups automaticos.

## Instalacion

### Linux / macOS

```bash
git clone https://github.com/mdwcoder/Work-CLI.git
cd Work-CLI/
chmod +x init.sh
./init.sh
```

### Windows PowerShell

```powershell
.\install.ps1
```

## Inicio rapido

```bash
work ON "Refactoring Login System"
work TIME
work OFF
```

## Comandos principales

| Comando | Accion |
| :--- | :--- |
| `work ON [Desc]` | Inicia temporizador |
| `work OFF` | Detiene sesion actual |
| `work TIME-TODAY` | Tiempo total de hoy |
| `work TIME-SELECT [Date]` | Tiempo de una fecha |
| `work TIME-RANGE [D1] [D2]` | Tiempo en rango |
| `work INIT-TIME` | Hora de inicio del dia |

## Uso recomendado

Utiliza Work-CLI para registrar sesiones de trabajo locales, generar informes y mantener datos sensibles bajo tu control.
