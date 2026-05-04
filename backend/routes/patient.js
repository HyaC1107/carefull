const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { parseNumericFields, validateRequiredFields } = require('../utils/validators');
const { sendSuccess, sendError } = require('../utils/response');

const validate_patient_payload = (body) => {
    const required_fields = [
        'patient_name',
        'birthdate',
        'gender',
        'bloodtype',
    ];

    return validateRequiredFields(body, required_fields);
};

const to_patient_response = (row) => ({
    patient_id: row.patient_id,
    mem_id: row.mem_id,
    patient_name: row.patient_name,
    birthdate: row.birthdate,
    gender: row.gender,
    phone: row.phone,
    address: row.address,
    bloodtype: row.bloodtype,
    height: row.height,
    weight: row.weight,
    fingerprint_slots: row.fingerprint_slots || [],
    guardian_name: row.guardian_name,
    guardian_phone: row.guardian_phone,
    created_at: row.created_at,
    updated_at: row.updated_at
});

router.post('/register', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    const {
        patient_name,
        birthdate,
        gender,
        phone,
        address,
        bloodtype,
        guardian_name,
        guardian_phone
    } = req.body;

    const validation_error = validate_patient_payload(req.body);
    if (validation_error) {
        return sendError(res, 400, validation_error);
    }

    const numeric_fields = parseNumericFields(req.body, [
        'height',
        'weight'
    ]);

    if (!numeric_fields) {
        return sendError(res, 400, 'height and weight must be numeric.');
    }

    const {
        height: parsed_height,
        weight: parsed_weight
    } = numeric_fields;

    try {
        const existing_patient_query = `
            SELECT patient_id
            FROM patients
            WHERE mem_id = $1
            LIMIT 1
        `;
        const existing_patient_result = await pool.query(existing_patient_query, [mem_id]);

        if (existing_patient_result.rows.length > 0) {
            return sendError(res, 409, 'Patient already exists.');
        }

        const insert_query = `
            INSERT INTO patients (
                mem_id,
                patient_name,
                birthdate,
                gender,
                phone,
                address,
                bloodtype,
                height,
                weight,
                guardian_name,
                guardian_phone
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            RETURNING
                patient_id,
                mem_id,
                patient_name,
                birthdate,
                gender,
                phone,
                address,
                bloodtype,
                height,
                weight,
                fingerprint_slots,
                guardian_name,
                guardian_phone,
                created_at,
                updated_at
        `;

        const { rows } = await pool.query(insert_query, [
            mem_id,
            patient_name,
            birthdate,
            gender,
            phone,
            address,
            bloodtype,
            parsed_height,
            parsed_weight,
            guardian_name,
            guardian_phone
        ]);

        return sendSuccess(res, 201, {
            message: 'Patient created successfully.',
            patient: to_patient_response(rows[0])
        });
    } catch (error) {
        console.error('Patient create error:', error);
        return sendError(res, 500, 'Server error while creating patient.');
    }
});

router.get('/me', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const select_query = `
            SELECT
                patient_id,
                mem_id,
                patient_name,
                birthdate,
                gender,
                phone,
                address,
                bloodtype,
                height,
                weight,
                fingerprint_slots,
                guardian_name,
                guardian_phone,
                created_at,
                updated_at
            FROM patients
            WHERE mem_id = $1
            LIMIT 1
        `;

        const { rows } = await pool.query(select_query, [mem_id]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Patient not found.');
        }

        return sendSuccess(res, 200, {
            patient: to_patient_response(rows[0])
        });
    } catch (error) {
        console.error('Patient fetch error:', error);
        return sendError(res, 500, 'Server error while fetching patient.');
    }
});

router.patch('/me', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const {
        patient_name,
        birthdate,
        gender,
        phone,
        address,
        bloodtype
    } = req.body;

    const validation_error = validate_patient_payload(req.body);
    if (validation_error) {
        return sendError(res, 400, validation_error);
    }

    const numeric_fields = parseNumericFields(req.body, [
        'height',
        'weight'
    ]);

    if (!numeric_fields) {
        return sendError(res, 400, 'height and weight must be numeric.');
    }

    const {
        height: parsed_height,
        weight: parsed_weight
    } = numeric_fields;

    try {
        const update_query = `
            UPDATE patients
            SET
                patient_name = $1,
                birthdate = $2,
                gender = $3,
                phone = $4,
                address = $5,
                bloodtype = $6,
                height = $7,
                weight = $8,
                updated_at = CURRENT_TIMESTAMP
            WHERE mem_id = $9
            RETURNING
                patient_id,
                mem_id,
                patient_name,
                birthdate,
                gender,
                phone,
                address,
                bloodtype,
                height,
                weight,
                fingerprint_slots,
                guardian_name,
                guardian_phone,
                created_at,
                updated_at
        `;

        const { rows } = await pool.query(update_query, [
            patient_name,
            birthdate,
            gender,
            phone,
            address,
            bloodtype,
            parsed_height,
            parsed_weight,
            mem_id
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Patient not found.');
        }

        return sendSuccess(res, 200, {
            message: 'Patient updated successfully.',
            patient: to_patient_response(rows[0])
        });
    } catch (error) {
        console.error('Patient patch error:', error);
        return sendError(res, 500, 'Server error while updating patient.');
    }
});

router.patch('/guardian', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;
    const {
        guardian_name,
        guardian_phone
    } = req.body;

    if (!guardian_name || !guardian_phone) {
        return sendError(res, 400, 'guardian_name and guardian_phone are required.');
    }

    try {
        const update_query = `
            UPDATE patients
            SET
                guardian_name = $1,
                guardian_phone = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE mem_id = $3
            RETURNING
                patient_id,
                mem_id,
                patient_name,
                birthdate,
                gender,
                phone,
                address,
                bloodtype,
                height,
                weight,
                fingerprint_slots,
                guardian_name,
                guardian_phone,
                created_at,
                updated_at
        `;

        const { rows } = await pool.query(update_query, [
            guardian_name,
            guardian_phone,
            mem_id
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Patient not found.');
        }

        return sendSuccess(res, 200, {
            message: 'Guardian updated successfully.',
            patient: to_patient_response(rows[0])
        });
    } catch (error) {
        console.error('Guardian patch error:', error);
        return sendError(res, 500, 'Server error while updating guardian.');
    }
});

router.put('/me', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    const {
        patient_name,
        birthdate,
        gender,
        phone,
        address,
        bloodtype,
        guardian_name,
        guardian_phone
    } = req.body;

    const validation_error = validate_patient_payload(req.body);
    if (validation_error) {
        return sendError(res, 400, validation_error);
    }

    const numeric_fields = parseNumericFields(req.body, [
        'height',
        'weight'
    ]);

    if (!numeric_fields) {
        return sendError(res, 400, 'height and weight must be numeric.');
    }

    const {
        height: parsed_height,
        weight: parsed_weight
    } = numeric_fields;

    try {
        const update_query = `
            UPDATE patients
            SET
                patient_name = $1,
                birthdate = $2,
                gender = $3,
                phone = $4,
                address = $5,
                bloodtype = $6,
                height = $7,
                weight = $8,
                guardian_name = $9,
                guardian_phone = $10,
                updated_at = CURRENT_TIMESTAMP
            WHERE mem_id = $11
            RETURNING
                patient_id,
                mem_id,
                patient_name,
                birthdate,
                gender,
                phone,
                address,
                bloodtype,
                height,
                weight,
                fingerprint_slots,
                guardian_name,
                guardian_phone,
                created_at,
                updated_at
        `;

        const { rows } = await pool.query(update_query, [
            patient_name,
            birthdate,
            gender,
            phone,
            address,
            bloodtype,
            parsed_height,
            parsed_weight,
            guardian_name,
            guardian_phone,
            mem_id
        ]);

        if (rows.length === 0) {
            return sendError(res, 404, 'Patient not found.');
        }

        return sendSuccess(res, 200, {
            message: 'Patient updated successfully.',
            patient: to_patient_response(rows[0])
        });
    } catch (error) {
        console.error('Patient update error:', error);
        return sendError(res, 500, 'Server error while updating patient.');
    }
});

module.exports = router;
