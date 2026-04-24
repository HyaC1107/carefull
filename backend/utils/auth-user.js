const pool = require('../db');

const find_patient_id_by_mem_id = async (mem_id) => {
    const query = `
        SELECT patient_id
        FROM patients
        WHERE mem_id = $1
        LIMIT 1
    `;

    const { rows } = await pool.query(query, [mem_id]);
    return rows.length > 0 ? rows[0].patient_id : null;
};

module.exports = {
    find_patient_id_by_mem_id
};
