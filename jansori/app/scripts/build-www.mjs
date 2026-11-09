// web/index.html 을 앱용 www/ 로 복사하면서 config.js, native.js 를 끼워 넣음
import { mkdirSync, readFileSync, writeFileSync, copyFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const www = join(root, "www");
mkdirSync(www, { recursive: true });

let html = readFileSync(join(root, "..", "web", "index.html"), "utf8");
const marker = "<script>\n(() => {";
if (!html.includes(marker)) throw new Error("index.html 의 메인 스크립트를 못 찾음");
html = html.replace(marker, '<script src="config.js"></script>\n<script src="native.js"></script>\n' + marker);
// 앱 안에서는 구글 폰트 대신 기기 글꼴을 써도 되지만, 인터넷이 되면 그대로 받아옴
writeFileSync(join(www, "index.html"), html);
copyFileSync(join(root, "src", "config.js"), join(www, "config.js"));
copyFileSync(join(root, "src", "native.js"), join(www, "native.js"));
console.log("www/ 준비 완료");
