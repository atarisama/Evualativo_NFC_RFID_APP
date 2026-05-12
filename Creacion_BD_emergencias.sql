CREATE DATABASE IF NOT EXISTS emergencias_nfc;
USE emergencias_nfc;

CREATE TABLE IF NOT EXISTS pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rfid_uid VARCHAR(50) UNIQUE NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    tipo_sangre VARCHAR(10) NOT NULL,
    alergias TEXT,
    condiciones_medicas TEXT,
    contacto_emergencia VARCHAR(100)
);