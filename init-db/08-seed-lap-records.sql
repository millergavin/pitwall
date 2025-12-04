-- Seed fastest lap records for all F1 circuits
-- Data sourced from Formula 1 official records (race lap records, not qualifying)

-- Melbourne - 1:19.813 = 79813ms - Charles Leclerc 2024
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 79813,
    fastest_lap_driver_id = 'drv:charles-leclerc',
    fastest_lap_driver_name = 'Charles Leclerc',
    fastest_lap_year = 2024
WHERE circuit_id = 'circuit:Melbourne-10';

-- Shanghai - 1:32.238 = 92238ms - Michael Schumacher 2004
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 92238,
    fastest_lap_driver_id = NULL,
    fastest_lap_driver_name = 'Michael Schumacher',
    fastest_lap_year = 2004
WHERE circuit_id = 'circuit:Shanghai-49';

-- Suzuka - 1:30.965 = 90965ms - Kimi Antonelli 2025
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 90965,
    fastest_lap_driver_id = 'drv:kimi-antonelli',
    fastest_lap_driver_name = 'Kimi Antonelli',
    fastest_lap_year = 2025
WHERE circuit_id = 'circuit:Suzuka-46';

-- Bahrain (Sakhir) - 1:31.447 = 91447ms - Pedro de la Rosa 2005
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 91447,
    fastest_lap_driver_id = NULL,
    fastest_lap_driver_name = 'Pedro de la Rosa',
    fastest_lap_year = 2005
WHERE circuit_id = 'circuit:Sakhir-63';

-- Jeddah - 1:30.734 = 90734ms - Lewis Hamilton 2021
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 90734,
    fastest_lap_driver_id = 'drv:lewis-hamilton',
    fastest_lap_driver_name = 'Lewis Hamilton',
    fastest_lap_year = 2021
WHERE circuit_id = 'circuit:Jeddah-149';

-- Miami - 1:29.708 = 89708ms - Max Verstappen 2023
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 89708,
    fastest_lap_driver_id = 'drv:max-verstappen',
    fastest_lap_driver_name = 'Max Verstappen',
    fastest_lap_year = 2023
WHERE circuit_id = 'circuit:Miami-151';

-- Imola - 1:15.484 = 75484ms - Lewis Hamilton 2020
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 75484,
    fastest_lap_driver_id = 'drv:lewis-hamilton',
    fastest_lap_driver_name = 'Lewis Hamilton',
    fastest_lap_year = 2020
WHERE circuit_id = 'circuit:Imola-6';

-- Monaco - 1:12.909 = 72909ms - Lewis Hamilton 2021
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 72909,
    fastest_lap_driver_id = 'drv:lewis-hamilton',
    fastest_lap_driver_name = 'Lewis Hamilton',
    fastest_lap_year = 2021
WHERE circuit_id = 'circuit:Monte Carlo-22';

-- Catalunya - 1:16.330 = 76330ms - Oscar Piastri 2025
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 76330,
    fastest_lap_driver_id = 'drv:oscar-piastri',
    fastest_lap_driver_name = 'Oscar Piastri',
    fastest_lap_year = 2025
WHERE circuit_id = 'circuit:Catalunya-15';

-- Montreal - 1:13.078 = 73078ms - Valtteri Bottas 2019
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 73078,
    fastest_lap_driver_id = 'drv:valtteri-bottas',
    fastest_lap_driver_name = 'Valtteri Bottas',
    fastest_lap_year = 2019
WHERE circuit_id = 'circuit:Montreal-23';

-- Spielberg (Red Bull Ring) - 1:05.619 = 65619ms - Carlos Sainz 2020
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 65619,
    fastest_lap_driver_id = 'drv:carlos-sainz',
    fastest_lap_driver_name = 'Carlos Sainz',
    fastest_lap_year = 2020
WHERE circuit_id = 'circuit:Spielberg-19';

-- Silverstone - 1:27.097 = 87097ms - Max Verstappen 2020
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 87097,
    fastest_lap_driver_id = 'drv:max-verstappen',
    fastest_lap_driver_name = 'Max Verstappen',
    fastest_lap_year = 2020
WHERE circuit_id = 'circuit:Silverstone-2';

-- Spa-Francorchamps - 1:44.701 = 104701ms - Sergio Perez 2024
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 104701,
    fastest_lap_driver_id = 'drv:sergio-perez',
    fastest_lap_driver_name = 'Sergio Perez',
    fastest_lap_year = 2024
WHERE circuit_id = 'circuit:Spa-Francorchamps-7';

-- Hungaroring - 1:16.627 = 76627ms - Lewis Hamilton 2020
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 76627,
    fastest_lap_driver_id = 'drv:lewis-hamilton',
    fastest_lap_driver_name = 'Lewis Hamilton',
    fastest_lap_year = 2020
WHERE circuit_id = 'circuit:Hungaroring-4';

-- Zandvoort - 1:11.097 = 71097ms - Lewis Hamilton 2021
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 71097,
    fastest_lap_driver_id = 'drv:lewis-hamilton',
    fastest_lap_driver_name = 'Lewis Hamilton',
    fastest_lap_year = 2021
WHERE circuit_id = 'circuit:Zandvoort-55';

-- Monza - 1:20.901 = 80901ms - Lando Norris 2025
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 80901,
    fastest_lap_driver_id = 'drv:lando-norris',
    fastest_lap_driver_name = 'Lando Norris',
    fastest_lap_year = 2025
WHERE circuit_id = 'circuit:Monza-39';

-- Baku - 1:43.009 = 103009ms - Charles Leclerc 2019
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 103009,
    fastest_lap_driver_id = 'drv:charles-leclerc',
    fastest_lap_driver_name = 'Charles Leclerc',
    fastest_lap_year = 2019
WHERE circuit_id = 'circuit:Baku-144';

-- Singapore - 1:33.808 = 93808ms - Lewis Hamilton 2025
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 93808,
    fastest_lap_driver_id = 'drv:lewis-hamilton',
    fastest_lap_driver_name = 'Lewis Hamilton',
    fastest_lap_year = 2025
WHERE circuit_id = 'circuit:Singapore-61';

-- Austin (COTA) - 1:36.169 = 96169ms - Charles Leclerc 2019
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 96169,
    fastest_lap_driver_id = 'drv:charles-leclerc',
    fastest_lap_driver_name = 'Charles Leclerc',
    fastest_lap_year = 2019
WHERE circuit_id = 'circuit:Austin-9';

-- Mexico City - 1:17.774 = 77774ms - Valtteri Bottas 2021
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 77774,
    fastest_lap_driver_id = 'drv:valtteri-bottas',
    fastest_lap_driver_name = 'Valtteri Bottas',
    fastest_lap_year = 2021
WHERE circuit_id = 'circuit:Mexico City-65';

-- Interlagos - 1:10.540 = 70540ms - Valtteri Bottas 2018
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 70540,
    fastest_lap_driver_id = 'drv:valtteri-bottas',
    fastest_lap_driver_name = 'Valtteri Bottas',
    fastest_lap_year = 2018
WHERE circuit_id = 'circuit:Interlagos-14';

-- Las Vegas - 1:35.490 = 95490ms - Oscar Piastri 2023
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 95490,
    fastest_lap_driver_id = 'drv:oscar-piastri',
    fastest_lap_driver_name = 'Oscar Piastri',
    fastest_lap_year = 2023
WHERE circuit_id = 'circuit:Las Vegas-152';

-- Lusail - 1:24.319 = 84319ms - Max Verstappen 2023
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 84319,
    fastest_lap_driver_id = 'drv:max-verstappen',
    fastest_lap_driver_name = 'Max Verstappen',
    fastest_lap_year = 2023
WHERE circuit_id = 'circuit:Lusail-150';

-- Yas Marina - 1:26.103 = 86103ms - Max Verstappen 2021
UPDATE silver.circuits SET 
    fastest_lap_time_ms = 86103,
    fastest_lap_driver_id = 'drv:max-verstappen',
    fastest_lap_driver_name = 'Max Verstappen',
    fastest_lap_year = 2021
WHERE circuit_id = 'circuit:Yas Marina Circuit-70';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON silver.circuits TO pitwall;

-- Verify the updates
SELECT 
    circuit_short_name,
    fastest_lap_time_ms,
    fastest_lap_driver_name,
    fastest_lap_year
FROM silver.circuits 
ORDER BY fastest_lap_time_ms;


