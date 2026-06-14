# Scripts

## Windows bootstrap

```powershell
.\scripts\bootstrap-windows.ps1
```

To install required tools through winget:

```powershell
.\scripts\bootstrap-windows.ps1 -InstallTools
```

If winget cannot reach package sources, install these manually:

- Python 3.12
- Node.js LTS
- Docker Desktop

For a backend syntax check without system Python:

```powershell
.\scripts\bootstrap-windows.ps1 -PortableValidationTools
```
