import http from 'k6/http';
import { sleep } from 'k6';

//k6 run 240615_upload_test.js --summary-trend-stats "min,avg,med,max,p(95),p(99),p(99.9)"

export const options = {
  vus: 20,
  duration: '10s',
};

const imageIndex = 1;
const urlIndex = 0; // 0: sync, 1: asyncio, 2: threadpool, 3: processpool

const images = [
    open('./test_image_1.png'), // chunsik
    open('./test_image_2.jpg') // 8K image
];

const image_filenames = [
    'test_image_1.png',
    'test_image_2.jpg',
];

const urls = [
    'http://127.0.0.1:8000/commiter/upload_sync', // 0
    'http://127.0.0.1:8000/commiter/upload_asyncio',  // 1
    'http://127.0.0.1:8000/commiter/upload_threadpool',  // 2
    'http://127.0.0.1:8000/commiter/upload_processpool',  // 3
    'http://127.0.0.1:8000/commiter/upload', // 4
    'http://127.0.0.1:8000/commiter/upload_background_task', // 5
];

export function setup(){
    console.log("image index: ", imageIndex, "url index: ", urlIndex )
}
export default function() {


    const data = {
        file: http.file(images[imageIndex], image_filenames[imageIndex]),
    };

  const res = http.post(urls[urlIndex], data);
  sleep(1);
}
