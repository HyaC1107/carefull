module.exports = {
    apps: [
        {
            name: 'carefull-api',
            script: 'server.js',
            instances: 1,
            exec_mode: 'fork',
            env_production: {
                NODE_ENV: 'production'
            },
            error_file: './logs/err.log',
            out_file: './logs/out.log',
            log_date_format: 'YYYY-MM-DD HH:mm:ss',
            max_memory_restart: '500M',
            restart_delay: 3000,
            max_restarts: 10
        }
    ]
};
