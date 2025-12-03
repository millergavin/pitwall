-- Seed turn data for all F1 circuits
-- This creates placeholder rows for each turn; coordinates and metadata can be enriched later

-- Bahrain - Sakhir (15 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Sakhir-63', 1),
    ('circuit:Sakhir-63', 2),
    ('circuit:Sakhir-63', 3),
    ('circuit:Sakhir-63', 4),
    ('circuit:Sakhir-63', 5),
    ('circuit:Sakhir-63', 6),
    ('circuit:Sakhir-63', 7),
    ('circuit:Sakhir-63', 8),
    ('circuit:Sakhir-63', 9),
    ('circuit:Sakhir-63', 10),
    ('circuit:Sakhir-63', 11),
    ('circuit:Sakhir-63', 12),
    ('circuit:Sakhir-63', 13),
    ('circuit:Sakhir-63', 14),
    ('circuit:Sakhir-63', 15)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Singapore - Marina Bay (23 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Singapore-61', 1),
    ('circuit:Singapore-61', 2),
    ('circuit:Singapore-61', 3),
    ('circuit:Singapore-61', 4),
    ('circuit:Singapore-61', 5),
    ('circuit:Singapore-61', 6),
    ('circuit:Singapore-61', 7),
    ('circuit:Singapore-61', 8),
    ('circuit:Singapore-61', 9),
    ('circuit:Singapore-61', 10),
    ('circuit:Singapore-61', 11),
    ('circuit:Singapore-61', 12),
    ('circuit:Singapore-61', 13),
    ('circuit:Singapore-61', 14),
    ('circuit:Singapore-61', 15),
    ('circuit:Singapore-61', 16),
    ('circuit:Singapore-61', 17),
    ('circuit:Singapore-61', 18),
    ('circuit:Singapore-61', 19),
    ('circuit:Singapore-61', 20),
    ('circuit:Singapore-61', 21),
    ('circuit:Singapore-61', 22),
    ('circuit:Singapore-61', 23)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Austria - Red Bull Ring (10 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Spielberg-19', 1),
    ('circuit:Spielberg-19', 2),
    ('circuit:Spielberg-19', 3),
    ('circuit:Spielberg-19', 4),
    ('circuit:Spielberg-19', 5),
    ('circuit:Spielberg-19', 6),
    ('circuit:Spielberg-19', 7),
    ('circuit:Spielberg-19', 8),
    ('circuit:Spielberg-19', 9),
    ('circuit:Spielberg-19', 10)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Netherlands - Zandvoort (14 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Zandvoort-55', 1),
    ('circuit:Zandvoort-55', 2),
    ('circuit:Zandvoort-55', 3),
    ('circuit:Zandvoort-55', 4),
    ('circuit:Zandvoort-55', 5),
    ('circuit:Zandvoort-55', 6),
    ('circuit:Zandvoort-55', 7),
    ('circuit:Zandvoort-55', 8),
    ('circuit:Zandvoort-55', 9),
    ('circuit:Zandvoort-55', 10),
    ('circuit:Zandvoort-55', 11),
    ('circuit:Zandvoort-55', 12),
    ('circuit:Zandvoort-55', 13),
    ('circuit:Zandvoort-55', 14)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- USA - Miami (19 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Miami-151', 1),
    ('circuit:Miami-151', 2),
    ('circuit:Miami-151', 3),
    ('circuit:Miami-151', 4),
    ('circuit:Miami-151', 5),
    ('circuit:Miami-151', 6),
    ('circuit:Miami-151', 7),
    ('circuit:Miami-151', 8),
    ('circuit:Miami-151', 9),
    ('circuit:Miami-151', 10),
    ('circuit:Miami-151', 11),
    ('circuit:Miami-151', 12),
    ('circuit:Miami-151', 13),
    ('circuit:Miami-151', 14),
    ('circuit:Miami-151', 15),
    ('circuit:Miami-151', 16),
    ('circuit:Miami-151', 17),
    ('circuit:Miami-151', 18),
    ('circuit:Miami-151', 19)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Spain - Catalunya (16 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Catalunya-15', 1),
    ('circuit:Catalunya-15', 2),
    ('circuit:Catalunya-15', 3),
    ('circuit:Catalunya-15', 4),
    ('circuit:Catalunya-15', 5),
    ('circuit:Catalunya-15', 6),
    ('circuit:Catalunya-15', 7),
    ('circuit:Catalunya-15', 8),
    ('circuit:Catalunya-15', 9),
    ('circuit:Catalunya-15', 10),
    ('circuit:Catalunya-15', 11),
    ('circuit:Catalunya-15', 12),
    ('circuit:Catalunya-15', 13),
    ('circuit:Catalunya-15', 14),
    ('circuit:Catalunya-15', 15),
    ('circuit:Catalunya-15', 16)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Italy - Monza (11 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Monza-39', 1),
    ('circuit:Monza-39', 2),
    ('circuit:Monza-39', 3),
    ('circuit:Monza-39', 4),
    ('circuit:Monza-39', 5),
    ('circuit:Monza-39', 6),
    ('circuit:Monza-39', 7),
    ('circuit:Monza-39', 8),
    ('circuit:Monza-39', 9),
    ('circuit:Monza-39', 10),
    ('circuit:Monza-39', 11)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Italy - Imola (17 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Imola-6', 1),
    ('circuit:Imola-6', 2),
    ('circuit:Imola-6', 3),
    ('circuit:Imola-6', 4),
    ('circuit:Imola-6', 5),
    ('circuit:Imola-6', 6),
    ('circuit:Imola-6', 7),
    ('circuit:Imola-6', 8),
    ('circuit:Imola-6', 9),
    ('circuit:Imola-6', 10),
    ('circuit:Imola-6', 11),
    ('circuit:Imola-6', 12),
    ('circuit:Imola-6', 13),
    ('circuit:Imola-6', 14),
    ('circuit:Imola-6', 15),
    ('circuit:Imola-6', 16),
    ('circuit:Imola-6', 17)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Azerbaijan - Baku (20 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Baku-144', 1),
    ('circuit:Baku-144', 2),
    ('circuit:Baku-144', 3),
    ('circuit:Baku-144', 4),
    ('circuit:Baku-144', 5),
    ('circuit:Baku-144', 6),
    ('circuit:Baku-144', 7),
    ('circuit:Baku-144', 8),
    ('circuit:Baku-144', 9),
    ('circuit:Baku-144', 10),
    ('circuit:Baku-144', 11),
    ('circuit:Baku-144', 12),
    ('circuit:Baku-144', 13),
    ('circuit:Baku-144', 14),
    ('circuit:Baku-144', 15),
    ('circuit:Baku-144', 16),
    ('circuit:Baku-144', 17),
    ('circuit:Baku-144', 18),
    ('circuit:Baku-144', 19),
    ('circuit:Baku-144', 20)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Hungary - Hungaroring (14 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Hungaroring-4', 1),
    ('circuit:Hungaroring-4', 2),
    ('circuit:Hungaroring-4', 3),
    ('circuit:Hungaroring-4', 4),
    ('circuit:Hungaroring-4', 5),
    ('circuit:Hungaroring-4', 6),
    ('circuit:Hungaroring-4', 7),
    ('circuit:Hungaroring-4', 8),
    ('circuit:Hungaroring-4', 9),
    ('circuit:Hungaroring-4', 10),
    ('circuit:Hungaroring-4', 11),
    ('circuit:Hungaroring-4', 12),
    ('circuit:Hungaroring-4', 13),
    ('circuit:Hungaroring-4', 14)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Brazil - Interlagos (15 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Interlagos-14', 1),
    ('circuit:Interlagos-14', 2),
    ('circuit:Interlagos-14', 3),
    ('circuit:Interlagos-14', 4),
    ('circuit:Interlagos-14', 5),
    ('circuit:Interlagos-14', 6),
    ('circuit:Interlagos-14', 7),
    ('circuit:Interlagos-14', 8),
    ('circuit:Interlagos-14', 9),
    ('circuit:Interlagos-14', 10),
    ('circuit:Interlagos-14', 11),
    ('circuit:Interlagos-14', 12),
    ('circuit:Interlagos-14', 13),
    ('circuit:Interlagos-14', 14),
    ('circuit:Interlagos-14', 15)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Saudi Arabia - Jeddah (27 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Jeddah-149', 1),
    ('circuit:Jeddah-149', 2),
    ('circuit:Jeddah-149', 3),
    ('circuit:Jeddah-149', 4),
    ('circuit:Jeddah-149', 5),
    ('circuit:Jeddah-149', 6),
    ('circuit:Jeddah-149', 7),
    ('circuit:Jeddah-149', 8),
    ('circuit:Jeddah-149', 9),
    ('circuit:Jeddah-149', 10),
    ('circuit:Jeddah-149', 11),
    ('circuit:Jeddah-149', 12),
    ('circuit:Jeddah-149', 13),
    ('circuit:Jeddah-149', 14),
    ('circuit:Jeddah-149', 15),
    ('circuit:Jeddah-149', 16),
    ('circuit:Jeddah-149', 17),
    ('circuit:Jeddah-149', 18),
    ('circuit:Jeddah-149', 19),
    ('circuit:Jeddah-149', 20),
    ('circuit:Jeddah-149', 21),
    ('circuit:Jeddah-149', 22),
    ('circuit:Jeddah-149', 23),
    ('circuit:Jeddah-149', 24),
    ('circuit:Jeddah-149', 25),
    ('circuit:Jeddah-149', 26),
    ('circuit:Jeddah-149', 27)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- USA - Las Vegas (17 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Las Vegas-152', 1),
    ('circuit:Las Vegas-152', 2),
    ('circuit:Las Vegas-152', 3),
    ('circuit:Las Vegas-152', 4),
    ('circuit:Las Vegas-152', 5),
    ('circuit:Las Vegas-152', 6),
    ('circuit:Las Vegas-152', 7),
    ('circuit:Las Vegas-152', 8),
    ('circuit:Las Vegas-152', 9),
    ('circuit:Las Vegas-152', 10),
    ('circuit:Las Vegas-152', 11),
    ('circuit:Las Vegas-152', 12),
    ('circuit:Las Vegas-152', 13),
    ('circuit:Las Vegas-152', 14),
    ('circuit:Las Vegas-152', 15),
    ('circuit:Las Vegas-152', 16),
    ('circuit:Las Vegas-152', 17)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Qatar - Lusail (16 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Lusail-150', 1),
    ('circuit:Lusail-150', 2),
    ('circuit:Lusail-150', 3),
    ('circuit:Lusail-150', 4),
    ('circuit:Lusail-150', 5),
    ('circuit:Lusail-150', 6),
    ('circuit:Lusail-150', 7),
    ('circuit:Lusail-150', 8),
    ('circuit:Lusail-150', 9),
    ('circuit:Lusail-150', 10),
    ('circuit:Lusail-150', 11),
    ('circuit:Lusail-150', 12),
    ('circuit:Lusail-150', 13),
    ('circuit:Lusail-150', 14),
    ('circuit:Lusail-150', 15),
    ('circuit:Lusail-150', 16)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Australia - Melbourne (14 turns - post 2022 reconfiguration)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Melbourne-10', 1),
    ('circuit:Melbourne-10', 2),
    ('circuit:Melbourne-10', 3),
    ('circuit:Melbourne-10', 4),
    ('circuit:Melbourne-10', 5),
    ('circuit:Melbourne-10', 6),
    ('circuit:Melbourne-10', 7),
    ('circuit:Melbourne-10', 8),
    ('circuit:Melbourne-10', 9),
    ('circuit:Melbourne-10', 10),
    ('circuit:Melbourne-10', 11),
    ('circuit:Melbourne-10', 12),
    ('circuit:Melbourne-10', 13),
    ('circuit:Melbourne-10', 14)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Mexico - Mexico City (17 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Mexico City-65', 1),
    ('circuit:Mexico City-65', 2),
    ('circuit:Mexico City-65', 3),
    ('circuit:Mexico City-65', 4),
    ('circuit:Mexico City-65', 5),
    ('circuit:Mexico City-65', 6),
    ('circuit:Mexico City-65', 7),
    ('circuit:Mexico City-65', 8),
    ('circuit:Mexico City-65', 9),
    ('circuit:Mexico City-65', 10),
    ('circuit:Mexico City-65', 11),
    ('circuit:Mexico City-65', 12),
    ('circuit:Mexico City-65', 13),
    ('circuit:Mexico City-65', 14),
    ('circuit:Mexico City-65', 15),
    ('circuit:Mexico City-65', 16),
    ('circuit:Mexico City-65', 17)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Monaco - Monte Carlo (19 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Monte Carlo-22', 1),
    ('circuit:Monte Carlo-22', 2),
    ('circuit:Monte Carlo-22', 3),
    ('circuit:Monte Carlo-22', 4),
    ('circuit:Monte Carlo-22', 5),
    ('circuit:Monte Carlo-22', 6),
    ('circuit:Monte Carlo-22', 7),
    ('circuit:Monte Carlo-22', 8),
    ('circuit:Monte Carlo-22', 9),
    ('circuit:Monte Carlo-22', 10),
    ('circuit:Monte Carlo-22', 11),
    ('circuit:Monte Carlo-22', 12),
    ('circuit:Monte Carlo-22', 13),
    ('circuit:Monte Carlo-22', 14),
    ('circuit:Monte Carlo-22', 15),
    ('circuit:Monte Carlo-22', 16),
    ('circuit:Monte Carlo-22', 17),
    ('circuit:Monte Carlo-22', 18),
    ('circuit:Monte Carlo-22', 19)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Canada - Montreal (14 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Montreal-23', 1),
    ('circuit:Montreal-23', 2),
    ('circuit:Montreal-23', 3),
    ('circuit:Montreal-23', 4),
    ('circuit:Montreal-23', 5),
    ('circuit:Montreal-23', 6),
    ('circuit:Montreal-23', 7),
    ('circuit:Montreal-23', 8),
    ('circuit:Montreal-23', 9),
    ('circuit:Montreal-23', 10),
    ('circuit:Montreal-23', 11),
    ('circuit:Montreal-23', 12),
    ('circuit:Montreal-23', 13),
    ('circuit:Montreal-23', 14)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Belgium - Spa-Francorchamps (19 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Spa-Francorchamps-7', 1),
    ('circuit:Spa-Francorchamps-7', 2),
    ('circuit:Spa-Francorchamps-7', 3),
    ('circuit:Spa-Francorchamps-7', 4),
    ('circuit:Spa-Francorchamps-7', 5),
    ('circuit:Spa-Francorchamps-7', 6),
    ('circuit:Spa-Francorchamps-7', 7),
    ('circuit:Spa-Francorchamps-7', 8),
    ('circuit:Spa-Francorchamps-7', 9),
    ('circuit:Spa-Francorchamps-7', 10),
    ('circuit:Spa-Francorchamps-7', 11),
    ('circuit:Spa-Francorchamps-7', 12),
    ('circuit:Spa-Francorchamps-7', 13),
    ('circuit:Spa-Francorchamps-7', 14),
    ('circuit:Spa-Francorchamps-7', 15),
    ('circuit:Spa-Francorchamps-7', 16),
    ('circuit:Spa-Francorchamps-7', 17),
    ('circuit:Spa-Francorchamps-7', 18),
    ('circuit:Spa-Francorchamps-7', 19)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- USA - Austin/COTA (20 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Austin-9', 1),
    ('circuit:Austin-9', 2),
    ('circuit:Austin-9', 3),
    ('circuit:Austin-9', 4),
    ('circuit:Austin-9', 5),
    ('circuit:Austin-9', 6),
    ('circuit:Austin-9', 7),
    ('circuit:Austin-9', 8),
    ('circuit:Austin-9', 9),
    ('circuit:Austin-9', 10),
    ('circuit:Austin-9', 11),
    ('circuit:Austin-9', 12),
    ('circuit:Austin-9', 13),
    ('circuit:Austin-9', 14),
    ('circuit:Austin-9', 15),
    ('circuit:Austin-9', 16),
    ('circuit:Austin-9', 17),
    ('circuit:Austin-9', 18),
    ('circuit:Austin-9', 19),
    ('circuit:Austin-9', 20)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- China - Shanghai (16 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Shanghai-49', 1),
    ('circuit:Shanghai-49', 2),
    ('circuit:Shanghai-49', 3),
    ('circuit:Shanghai-49', 4),
    ('circuit:Shanghai-49', 5),
    ('circuit:Shanghai-49', 6),
    ('circuit:Shanghai-49', 7),
    ('circuit:Shanghai-49', 8),
    ('circuit:Shanghai-49', 9),
    ('circuit:Shanghai-49', 10),
    ('circuit:Shanghai-49', 11),
    ('circuit:Shanghai-49', 12),
    ('circuit:Shanghai-49', 13),
    ('circuit:Shanghai-49', 14),
    ('circuit:Shanghai-49', 15),
    ('circuit:Shanghai-49', 16)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Japan - Suzuka (18 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Suzuka-46', 1),
    ('circuit:Suzuka-46', 2),
    ('circuit:Suzuka-46', 3),
    ('circuit:Suzuka-46', 4),
    ('circuit:Suzuka-46', 5),
    ('circuit:Suzuka-46', 6),
    ('circuit:Suzuka-46', 7),
    ('circuit:Suzuka-46', 8),
    ('circuit:Suzuka-46', 9),
    ('circuit:Suzuka-46', 10),
    ('circuit:Suzuka-46', 11),
    ('circuit:Suzuka-46', 12),
    ('circuit:Suzuka-46', 13),
    ('circuit:Suzuka-46', 14),
    ('circuit:Suzuka-46', 15),
    ('circuit:Suzuka-46', 16),
    ('circuit:Suzuka-46', 17),
    ('circuit:Suzuka-46', 18)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- UK - Silverstone (18 turns)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Silverstone-2', 1),
    ('circuit:Silverstone-2', 2),
    ('circuit:Silverstone-2', 3),
    ('circuit:Silverstone-2', 4),
    ('circuit:Silverstone-2', 5),
    ('circuit:Silverstone-2', 6),
    ('circuit:Silverstone-2', 7),
    ('circuit:Silverstone-2', 8),
    ('circuit:Silverstone-2', 9),
    ('circuit:Silverstone-2', 10),
    ('circuit:Silverstone-2', 11),
    ('circuit:Silverstone-2', 12),
    ('circuit:Silverstone-2', 13),
    ('circuit:Silverstone-2', 14),
    ('circuit:Silverstone-2', 15),
    ('circuit:Silverstone-2', 16),
    ('circuit:Silverstone-2', 17),
    ('circuit:Silverstone-2', 18)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- UAE - Yas Marina (16 turns - post 2021 reconfiguration)
INSERT INTO silver.turns (circuit_id, turn_number) VALUES
    ('circuit:Yas Marina Circuit-70', 1),
    ('circuit:Yas Marina Circuit-70', 2),
    ('circuit:Yas Marina Circuit-70', 3),
    ('circuit:Yas Marina Circuit-70', 4),
    ('circuit:Yas Marina Circuit-70', 5),
    ('circuit:Yas Marina Circuit-70', 6),
    ('circuit:Yas Marina Circuit-70', 7),
    ('circuit:Yas Marina Circuit-70', 8),
    ('circuit:Yas Marina Circuit-70', 9),
    ('circuit:Yas Marina Circuit-70', 10),
    ('circuit:Yas Marina Circuit-70', 11),
    ('circuit:Yas Marina Circuit-70', 12),
    ('circuit:Yas Marina Circuit-70', 13),
    ('circuit:Yas Marina Circuit-70', 14),
    ('circuit:Yas Marina Circuit-70', 15),
    ('circuit:Yas Marina Circuit-70', 16)
ON CONFLICT (circuit_id, turn_number) DO NOTHING;

-- Verify insertion
SELECT 
    c.circuit_short_name,
    COUNT(t.turn_number) as total_turns
FROM silver.circuits c
LEFT JOIN silver.turns t ON c.circuit_id = t.circuit_id
GROUP BY c.circuit_id, c.circuit_short_name
ORDER BY total_turns DESC;
