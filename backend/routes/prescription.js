const express = require('express');
const multer = require('multer');
const path = require('path');

const router = express.Router();

const { verifyToken } = require('../middleware/auth');
const { sendSuccess, sendError } = require('../utils/response');
const { analyze_prescription_image } = require('../services/prescription-ai.service');

const allowed_mime_types = new Set([
    'image/jpeg',
    'image/png',
    'image/webp'
]);

const allowed_extensions = new Set([
    '.jpg',
    '.jpeg',
    '.png',
    '.webp'
]);

const upload = multer({
    storage: multer.memoryStorage(),
    fileFilter: (req, file, callback) => {
        const file_extension = path.extname(file.originalname || '').toLowerCase();

        if (!allowed_mime_types.has(file.mimetype) || !allowed_extensions.has(file_extension)) {
            return callback(new Error('Only jpg, jpeg, png, and webp image files are allowed.'));
        }

        return callback(null, true);
    }
}).single('prescription_image');

router.post('/analyze', verifyToken, (req, res) => {
    upload(req, res, async (upload_error) => {
        if (upload_error instanceof multer.MulterError) {
            return sendError(res, 400, upload_error.message);
        }

        if (upload_error) {
            return sendError(res, 400, upload_error.message || 'Invalid prescription image upload.');
        }

        if (!req.file) {
            return sendError(res, 400, 'prescription_image is required.');
        }

        try {
            const draft = await analyze_prescription_image(req.file);

            return sendSuccess(res, 200, {
                message: 'Prescription analysis completed. Please review before registration.',
                draft
            });
        } catch (error) {
            console.error('Prescription analyze error:', error);
            return sendError(
                res,
                error.status_code || 500,
                error.message || 'Server error while analyzing prescription.'
            );
        }
    });
});

module.exports = router;
