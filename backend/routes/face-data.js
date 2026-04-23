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

module.exports = router;
