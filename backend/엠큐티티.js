// // [1] 필수 모듈 임포트
// const mqtt = require('mqtt'); // MQTT 통신을 위한 라이브러리
// const pool = require('./db'); // DB 저장을 위해 기존에 만든 db.js 불러오기

// // [2] MQTT 브로커 연결 설정 
// // 테스트를 위해 공용 브로커(broker.emqx.io)를 사용하거나 
// // 본인의 브로커 주소를 입력하면 돼!
// const brokerUrl = 'mqtt://broker.emqx.io'; 
// const client = mqtt.connect(brokerUrl);

// // [3] 브로커 연결 시 동작
// client.on('connect', () => {
//     console.log('MQTT 브로커에 성공적으로 연결됐어, 랑랑!');
    
//     // 라즈베리 파이가 보낼 메시지 주제(Topic)를 구독해
//     // 주제: carefull/medication/result (복약 결과)
//     client.subscribe('carefull/medication/result', (err) => {
//         if (!err) {
//             console.log('복약 결과 토픽 구독 시작!');
//         }
//     });
// });

// // [4] 메시지 수신 시 처리 로직
// client.on('message', async (topic, message) => {
//     // 수신된 메시지는 Buffer 형태라 문자열로 변환이 필요해
//     const payload = message.toString();
//     console.log(`[${topic}] 수신된 메시지: ${payload}`);

//     if (topic === 'carefull/medication/result') {
//         try {
//             // 메시지가 JSON 형태라고 가정하고 파싱해
//             const data = JSON.parse(payload);
//             const { userId, status, takenAt } = data;

//             // 수신 즉시 PostgreSQL DB에 저장!
//             const query = `
//                 INSERT INTO medication_logs (user_id, status, taken_at)
//                 VALUES ($1, $2, $3)
//             `;
//             await pool.query(query, [userId, status, takenAt]);
            
//             console.log('MQTT로 받은 복약 로그 저장 완료!');
//         } catch (error) {
//             console.error('MQTT 메시지 처리 중 에러 발생:', error);
//         }
//     }
// });

// // [5] 서버에서 기기로 명령을 보낼 때 쓰는 함수 (수출용)
// // 예: 보호자가 앱에서 '지금 약 먹으라고 알림 주기' 버튼을 눌렀을 때
// const sendNotification = (deviceId, message) => {
//     const topic = `carefull/command/${deviceId}`;
//     client.publish(topic, JSON.stringify({ msg: message }));
//     console.log(`${topic} 경로로 명령 전송: ${message}`);
// };

// // 다른 파일에서 쓸 수 있게 함수 수출!
// module.exports = { client, sendNotification };