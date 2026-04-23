const express = require('express');
const router = express.Router();

const pool = require('../db');
const { verifyToken } = require('../middleware/auth');
const { find_patient_id_by_mem_id } = require('../utils/auth-user');
const { sendSuccess, sendError } = require('../utils/response');
const { validateRequiredFields } = require('../utils/validators');

const validate_face_data_payload = (body) => {
    const required_fields = ['face_vector'];
    return validateRequiredFields(body, required_fields);
};

const normalize_embedding_value = (embedding) => {
    if (!Array.isArray(embedding) || embedding.length === 0) {
        return null;
    }

    const parsed_embedding = [];

    for (const value of embedding) {
        const parsed_value = Number(value);

        if (Number.isNaN(parsed_value)) {
            return null;
        }

        parsed_embedding.push(parsed_value);
    }

    return `[${parsed_embedding.join(',')}]`;
};

const to_face_embedding_response = (row) => ({
    face_id: row.face_id,
    patient_id: row.patient_id,
    face_vector: row.face_vector,
    created_at: row.created_at
});

router.post('/', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    const validation_error = validate_face_data_payload(req.body);
    if (validation_error) {
        return sendError(res, 400, validation_error);
    }

    const { face_vector } = req.body;
    const normalized_embedding = normalize_embedding_value(face_vector);

    if (!normalized_embedding) {
        return sendError(res, 400, 'face_vector must be a numeric array.');
    }

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const insert_query = `
            INSERT INTO face_embeddings (
                patient_id,
                face_vector
            )
            VALUES ($1, $2)
            RETURNING
                face_id,
                patient_id,
                face_vector,
                created_at
        `;

        const { rows } = await pool.query(insert_query, [
            patient_id,
            normalized_embedding
        ]);

        return sendSuccess(res, 201, {
            message: 'Face embedding created successfully.',
            face_embedding: to_face_embedding_response(rows[0])
        });
    } catch (error) {
        console.error('Face embedding create error:', error);
        return sendError(res, 500, 'Server error while creating face embedding.');
    }
});

router.get('/', verifyToken, async (req, res) => {
    const mem_id = req.user.mem_id;

    try {
        const patient_id = await find_patient_id_by_mem_id(mem_id);

        if (!patient_id) {
            return sendError(res, 404, 'Patient not found.');
        }

        const query = `
            SELECT
                face_id,
                patient_id,
                face_vector,
                created_at
            FROM face_embeddings
            WHERE patient_id = $1
            ORDER BY created_at DESC, face_id DESC
        `;

        const { rows } = await pool.query(query, [patient_id]);

        return sendSuccess(res, 200, {
            face_embeddings: rows.map(to_face_embedding_response)
        });
    } catch (error) {
        console.error('Face embedding fetch error:', error);
        return sendError(res, 500, 'Server error while fetching face embeddings.');
    }
});

// GET /api/face-data/device  — JWT 불필요, device_uid 로 인증
router.get('/device', async (req, res) => {
    const { device_uid } = req.query;

    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }

    try {
        const query = `
            SELECT
                fe.face_id,
                fe.patient_id,
                fe.face_vector,
                fe.created_at
            FROM face_embeddings fe
            INNER JOIN devices d ON d.patient_id = fe.patient_id
            WHERE d.device_uid = $1
            ORDER BY fe.created_at DESC, fe.face_id DESC
        `;

        const { rows } = await pool.query(query, [String(device_uid).trim()]);

        return sendSuccess(res, 200, {
            face_embeddings: rows.map(to_face_embedding_response)
        });
    } catch (error) {
        console.error('Device face embedding fetch error:', error);
        return sendError(res, 500, 'Server error while fetching device face embeddings.');
    }
});

// POST /api/face-data/device  — JWT 불필요, device_uid 로 인증
router.post('/device', async (req, res) => {
    const { device_uid, face_vector } = req.body;

    if (!device_uid || !String(device_uid).trim()) {
        return sendError(res, 400, 'device_uid is required.');
    }

    if (!face_vector) {
        return sendError(res, 400, 'face_vector is required.');
    }

    const normalized_embedding = normalize_embedding_value(face_vector);
    if (!normalized_embedding) {
        return sendError(res, 400, 'face_vector must be a numeric array.');
    }

    try {
        const device_query = `
            SELECT patient_id
            FROM devices
            WHERE device_uid = $1
              AND patient_id IS NOT NULL
            LIMIT 1
        `;
        const device_result = await pool.query(device_query, [String(device_uid).trim()]);

        if (device_result.rows.length === 0) {
            return sendError(res, 404, 'Device not found or not assigned to a patient.');
        }

        const { patient_id } = device_result.rows[0];

        const insert_query = `
            INSERT INTO face_embeddings (patient_id, face_vector)
            VALUES ($1, $2)
            RETURNING face_id, patient_id, face_vector, created_at
        `;

        const { rows } = await pool.query(insert_query, [patient_id, normalized_embedding]);

        return sendSuccess(res, 201, {
            message: 'Face embedding created successfully.',
            face_embedding: to_face_embedding_response(rows[0])
        });
    } catch (error) {
        console.error('Device face embedding create error:', error);
        return sendError(res, 500, 'Server error while creating device face embedding.');
    }
});

module.exports = router;
