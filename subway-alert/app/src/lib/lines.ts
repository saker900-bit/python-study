// 수도권 전철 노선 목록 (서버 server/app/lines.py 와 id 를 맞춰야 함)
export type Line = { id: string; name: string; color: string };

export const LINES: Line[] = [
  { id: "1", name: "1호선", color: "#0052A4" },
  { id: "2", name: "2호선", color: "#00A84D" },
  { id: "3", name: "3호선", color: "#EF7C1C" },
  { id: "4", name: "4호선", color: "#00A5DE" },
  { id: "5", name: "5호선", color: "#996CAC" },
  { id: "6", name: "6호선", color: "#CD7C2F" },
  { id: "7", name: "7호선", color: "#747F00" },
  { id: "8", name: "8호선", color: "#E6186C" },
  { id: "9", name: "9호선", color: "#BDB092" },
  { id: "shinbundang", name: "신분당선", color: "#D4003B" },
  { id: "suinbundang", name: "수인분당선", color: "#F5A200" },
  { id: "gyeongui", name: "경의중앙선", color: "#77C4A3" },
  { id: "airport", name: "공항철도", color: "#0090D2" },
  { id: "gyeongchun", name: "경춘선", color: "#0C8E72" },
  { id: "seohae", name: "서해선", color: "#81A914" },
  { id: "gtxa", name: "GTX-A", color: "#9A6292" },
  { id: "incheon1", name: "인천1호선", color: "#7CA8D5" },
  { id: "incheon2", name: "인천2호선", color: "#ED8B00" },
  { id: "uisinseol", name: "우이신설선", color: "#B0CE18" },
  { id: "sillim", name: "신림선", color: "#6789CA" },
  { id: "gimpo", name: "김포골드라인", color: "#AD8605" },
  { id: "everline", name: "용인에버라인", color: "#56AD2D" },
  { id: "uijeongbu", name: "의정부경전철", color: "#FDA600" },
];

export const lineById = (id: string | null | undefined) =>
  LINES.find((l) => l.id === id);
