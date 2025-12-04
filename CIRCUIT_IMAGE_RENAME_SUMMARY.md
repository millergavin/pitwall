# Circuit Image Folder Rename - Summary

## Overview
Renamed circuit image folders from generic/country names to match the `circuit_short_name` values from the database for cleaner mapping and consistency.

## Changes Made

### 1. Folder Renames (24 folders)

| Old Folder Name | New Folder Name | Circuit ID |
|----------------|-----------------|------------|
| abudhabi | Yas Marina Circuit | circuit:Yas Marina Circuit-70 |
| australia | Melbourne | circuit:Melbourne-10 |
| austria | Spielberg | circuit:Spielberg-19 |
| azerbaijan | Baku | circuit:Baku-144 |
| bahrain | Sakhir | circuit:Sakhir-63 |
| brazil | Interlagos | circuit:Interlagos-14 |
| canada | Montreal | circuit:Montreal-23 |
| china | Shanghai | circuit:Shanghai-49 |
| hungary | Hungaroring | circuit:Hungaroring-4 |
| imola | Imola | circuit:Imola-6 (case change) |
| japan | Suzuka | circuit:Suzuka-46 |
| las_vegas | Las Vegas | circuit:Las Vegas-152 |
| mexico | Mexico City | circuit:Mexico City-65 |
| miami | Miami | circuit:Miami-151 (case change) |
| monaco | Monte Carlo | circuit:Monte Carlo-22 |
| monza | Monza | circuit:Monza-39 (case change) |
| netherlands | Zandvoort | circuit:Zandvoort-55 |
| qatar | Lusail | circuit:Lusail-150 |
| saudi_arabia | Jeddah | circuit:Jeddah-149 |
| silverstone | Silverstone | circuit:Silverstone-2 (case change) |
| singapore | Singapore | circuit:Singapore-61 (case change) |
| spa | Spa-Francorchamps | circuit:Spa-Francorchamps-7 |
| spain | Catalunya | circuit:Catalunya-15 |
| usa | Austin | circuit:Austin-9 |

### 2. Database Updates

- **Table Updated:** `silver.images`
- **Total Records Updated:** 295 image paths
- **Update Pattern:** Changed `file_path` from `old_folder/filename.ext` to `new_folder/filename.ext`

### 3. Impact

All circuit image paths in the database now match the folder structure in:
```
/frontend/public/assets/circuit_image/
```

This ensures consistency between the filesystem and database, making it easier to:
- Query images by circuit_short_name
- Maintain the image library
- Debug image loading issues
- Understand the folder structure

### 4. Files Affected

The frontend references these images in:
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/CircuitDetails.tsx`
- `frontend/src/pages/MeetingDetails.tsx`
- `frontend/src/pages/Circuits.tsx`
- `frontend/src/pages/GrandPrix.tsx`

All references use the `file_path` from the database, so they automatically work with the updated paths.

## Verification

Database paths verified for sample circuits:
```sql
SELECT circuit_id, file_path 
FROM silver.images 
WHERE circuit_id = 'circuit:Austin-9' 
LIMIT 5;
```

Results show paths like:
- `Austin/formula-1-grand-prix-austin.jpg`
- `Austin/COTA_F1-2000x1333.jpg`
- etc.

## Date
December 3, 2025


