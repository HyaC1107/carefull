const pool = require('../db');

const PATIENT_SELECT_FIELDS = `
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
    fingerprint_id,
    guardian_name,
    guardian_phone,
    created_at,
    updated_at
`;

const pick_latest_patient_row = (mem_id, rows) => {
    if (rows.length === 0) {
        return null;
    }

    const sorted_rows = [...rows].sort((left, right) => right.patient_id - left.patient_id);

    if (sorted_rows.length > 1) {
        console.warn(
            `[patients] duplicate patient rows detected for mem_id=${mem_id}; using patient_id=${sorted_rows[0].patient_id} and ignoring ${sorted_rows.length - 1} older row(s).`
        );
    }

    return sorted_rows[0];
};

const find_latest_patient_by_mem_id = async (executor, mem_id) => {
    const query = `
        SELECT
            ${PATIENT_SELECT_FIELDS}
        FROM patients
        WHERE mem_id = $1
    `;

    const { rows } = await executor.query(query, [mem_id]);
    return pick_latest_patient_row(mem_id, rows);
};

const find_patient_id_by_mem_id = async (mem_id, executor = pool) => {
    const patient = await find_latest_patient_by_mem_id(executor, mem_id);
    return patient ? patient.patient_id : null;
};

module.exports = {
    find_latest_patient_by_mem_id,
    find_patient_id_by_mem_id
};
