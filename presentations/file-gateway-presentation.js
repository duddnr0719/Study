const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

// react-icons
const { FaSlack, FaDocker, FaServer, FaShieldAlt, FaFolder, FaFileUpload,
        FaFileDownload, FaSearch, FaLock, FaExclamationTriangle,
        FaCheckCircle, FaBug, FaCog } = require("react-icons/fa");
const { MdSecurity, MdSpeed, MdStorage } = require("react-icons/md");

// ── 아이콘 → PNG base64 변환 ──
function renderIconSvg(IconComponent, color = "#FFFFFF", size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}
async function iconPng(IconComponent, color = "#FFFFFF", size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ── 색상 팔레트 ──
const C = {
  navy:    "0D1B2A",  // 짙은 네이비 (타이틀 배경)
  dark:    "1A2744",  // 어두운 블루
  blue:    "1565C0",  // 강조 블루
  teal:    "00897B",  // 틸
  red:     "C62828",  // 위험/에러
  orange:  "E65100",  // 경고
  yellow:  "F9A825",  // 주의
  green:   "2E7D32",  // 완료
  white:   "FFFFFF",
  light:   "F4F6F8",
  gray:    "546E7A",
  lgray:   "ECEFF1",
  text:    "1A1A2E",
};

async function buildPptx() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = "File Gateway";

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 1 — 타이틀
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };

    // 왼쪽 파란 세로 바
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 0.18, h: 5.625,
      fill: { color: C.blue }, line: { color: C.blue }
    });

    // 아이콘
    const slackIcon = await iconPng(FaSlack, "#FFFFFF", 256);
    sl.addImage({ data: slackIcon, x: 0.5, y: 1.5, w: 0.8, h: 0.8 });

    const serverIcon = await iconPng(FaServer, "#FFFFFF", 256);
    sl.addImage({ data: serverIcon, x: 2.1, y: 1.5, w: 0.8, h: 0.8 });

    // 화살표 텍스트
    sl.addText("⟷", { x: 1.35, y: 1.6, w: 0.7, h: 0.6, fontSize: 28,
      color: C.teal.replace("00", "00"), fontFace: "Arial", align: "center" });
    sl.addText("⟷", { x: 1.35, y: 1.6, w: 0.7, h: 0.6, fontSize: 26,
      color: "00BCD4", fontFace: "Arial", align: "center" });

    // 메인 타이틀
    sl.addText("File Gateway", {
      x: 0.4, y: 2.4, w: 9.2, h: 1.1,
      fontSize: 52, bold: true, color: C.white, fontFace: "Arial Black",
      align: "left", margin: 0
    });

    // 서브타이틀
    sl.addText("Slack ↔ 연구실 서버 공유폴더 파일 브릿지", {
      x: 0.4, y: 3.5, w: 9.2, h: 0.55,
      fontSize: 20, color: "90CAF9", fontFace: "Arial", align: "left", margin: 0
    });

    // 태그라인
    sl.addText("Terminal 없이 Slack에서 직접 파일 관리", {
      x: 0.4, y: 4.1, w: 9.2, h: 0.45,
      fontSize: 15, color: "78909C", fontFace: "Arial", align: "left",
      italic: true, margin: 0
    });

    // 우하단 태그
    const tags = ["Python · Slack Bolt", "Docker", "Socket Mode", "Threading"];
    tags.forEach((t, i) => {
      sl.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 5.5 + i * 1.1, y: 4.9, w: 1.0, h: 0.38,
        fill: { color: C.dark }, line: { color: C.blue }, rectRadius: 0.06
      });
      sl.addText(t, {
        x: 5.5 + i * 1.1, y: 4.9, w: 1.0, h: 0.38,
        fontSize: 9, color: "90CAF9", align: "center", bold: true
      });
    });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 헬퍼: 콘텐츠 슬라이드 헤더
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  function addHeader(sl, title, accentColor = C.blue) {
    sl.background = { color: C.light };
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 0.75,
      fill: { color: accentColor }, line: { color: accentColor }
    });
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0.75, w: 10, h: 0.04,
      fill: { color: "BBDEFB" }, line: { color: "BBDEFB" }
    });
    sl.addText(title, {
      x: 0.35, y: 0, w: 9.3, h: 0.75,
      fontSize: 22, bold: true, color: C.white, fontFace: "Arial",
      valign: "middle", margin: 0
    });
    // 슬라이드 번호 영역 하단 바
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 5.35, w: 10, h: 0.275,
      fill: { color: "E3F2FD" }, line: { color: "E3F2FD" }
    });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 2 — 프로젝트 배경 & 목적
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    addHeader(sl, "01  프로젝트 배경 & 목적");

    const cards = [
      { icon: FaExclamationTriangle, color: C.orange, title: "문제",
        lines: ["연구실 공유폴더 접근에 매번", "터미널 + SSH + 경로 입력 필요", "비개발자 연구원에게 진입장벽 높음"] },
      { icon: FaCheckCircle, color: C.teal, title: "해결책",
        lines: ["Slack에서 명령어 한 줄로", "파일 저장·다운로드·탐색", "누구나 쉽게 공유폴더 관리"] },
      { icon: FaCog, color: C.blue, title: "목표",
        lines: ["Slack Pro 플랜 활용 극대화", "연구실 워크플로우 자동화", "파일 관리 진입장벽 제거"] },
    ];

    for (let i = 0; i < cards.length; i++) {
      const x = 0.35 + i * 3.15;
      // 카드 배경
      sl.addShape(pres.shapes.RECTANGLE, {
        x, y: 0.95, w: 2.9, h: 4.1,
        fill: { color: C.white },
        shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.1 }
      });
      // 상단 컬러 바
      sl.addShape(pres.shapes.RECTANGLE, {
        x, y: 0.95, w: 2.9, h: 0.08,
        fill: { color: cards[i].color }, line: { color: cards[i].color }
      });
      // 아이콘 원 배경
      sl.addShape(pres.shapes.OVAL, {
        x: x + 1.05, y: 1.2, w: 0.8, h: 0.8,
        fill: { color: cards[i].color, transparency: 15 }, line: { color: cards[i].color }
      });
      const ic = await iconPng(cards[i].icon, "#FFFFFF", 256);
      sl.addImage({ data: ic, x: x + 1.2, y: 1.33, w: 0.5, h: 0.5 });
      // 제목
      sl.addText(cards[i].title, {
        x: x + 0.1, y: 2.1, w: 2.7, h: 0.45,
        fontSize: 18, bold: true, color: cards[i].color, align: "center"
      });
      // 내용
      const lineTexts = cards[i].lines.map((l, idx) => ({
        text: l,
        options: { breakLine: idx < cards[i].lines.length - 1 }
      }));
      sl.addText(lineTexts, {
        x: x + 0.15, y: 2.65, w: 2.6, h: 2.1,
        fontSize: 13, color: C.text, align: "center", valign: "top",
        lineSpacingMultiple: 1.4
      });
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 3 — 시스템 아키텍처
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    addHeader(sl, "02  시스템 아키텍처");

    // Slack 박스
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y: 1.0, w: 2.8, h: 3.8,
      fill: { color: "4A154B" }, line: { color: "4A154B" }
    });
    sl.addText("Slack", { x: 0.3, y: 1.0, w: 2.8, h: 0.5,
      fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle" });
    const slackIc = await iconPng(FaSlack, "#FFFFFF", 256);
    sl.addImage({ data: slackIc, x: 1.2, y: 1.55, w: 1.0, h: 1.0 });
    const cmds = ["/ls  /cd  /pwd", "/save  /fetch", "/create"];
    cmds.forEach((c, i) => {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 0.45, y: 2.75 + i * 0.55, w: 2.5, h: 0.42,
        fill: { color: "6B2D7B" }, line: { color: "7B3D8B" }
      });
      sl.addText(c, { x: 0.45, y: 2.75 + i * 0.55, w: 2.5, h: 0.42,
        fontSize: 11, color: "E1BEE7", align: "center", valign: "middle",
        fontFace: "Consolas" });
    });

    // 화살표 Socket Mode
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 3.15, y: 2.3, w: 1.5, h: 0.04,
      fill: { color: C.teal }, line: { color: C.teal }
    });
    sl.addText("◀▶", { x: 3.1, y: 2.0, w: 1.6, h: 0.3,
      fontSize: 14, color: "00BCD4", align: "center" });
    sl.addText("Socket Mode", { x: 3.1, y: 2.35, w: 1.6, h: 0.3,
      fontSize: 10, color: C.teal, align: "center", bold: true });
    sl.addText("(WebSocket)", { x: 3.1, y: 2.65, w: 1.6, h: 0.25,
      fontSize: 9, color: C.gray, align: "center" });

    // 서버 박스
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 4.7, y: 1.0, w: 5.0, h: 3.8,
      fill: { color: C.dark }, line: { color: C.blue }
    });
    sl.addText("Docker Container (서버)", { x: 4.7, y: 1.0, w: 5.0, h: 0.45,
      fontSize: 13, bold: true, color: "90CAF9", align: "center", valign: "middle" });

    const serverIc = await iconPng(FaDocker, "#0288D1", 256);
    sl.addImage({ data: serverIc, x: 5.0, y: 1.5, w: 0.55, h: 0.55 });
    sl.addText("app.py  (Slack Bolt)", { x: 5.6, y: 1.55, w: 3.8, h: 0.45,
      fontSize: 13, bold: true, color: C.white, valign: "middle" });

    const components = [
      ["슬래시 명령어 핸들러", C.blue],
      ["파일 다운로드 / 업로드 (스트리밍)", "00897B"],
      ["상태 관리 + 영속성 (state.json)", "7B1FA2"],
      ["백그라운드 cleanup 스레드", "E65100"],
    ];
    components.forEach(([label, color], i) => {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 4.85, y: 2.1 + i * 0.52, w: 0.12, h: 0.35,
        fill: { color }, line: { color }
      });
      sl.addText(label, { x: 5.05, y: 2.1 + i * 0.52, w: 4.5, h: 0.35,
        fontSize: 11, color: "CFD8DC", valign: "middle" });
    });

    // 스토리지
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 4.85, y: 4.2, w: 4.65, h: 0.45,
      fill: { color: "1B5E20" }, line: { color: "2E7D32" }
    });
    const storIc = await iconPng(MdStorage, "#FFFFFF", 256);
    sl.addImage({ data: storIc, x: 4.9, y: 4.24, w: 0.38, h: 0.38 });
    sl.addText("/storage → ecsamba/shared (Samba + Tailscale VPN)", {
      x: 5.35, y: 4.2, w: 4.1, h: 0.45,
      fontSize: 11, color: "A5D6A7", valign: "middle" });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 4 — 주요 기능
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    addHeader(sl, "03  주요 기능");

    const features = [
      { cmd: "save <경로>",    icon: FaFileUpload,   color: C.teal,   desc: "파일 첨부 + 메시지로 서버에 저장\n중복 시 덮어쓰기 / 새이름 / 취소 선택" },
      { cmd: "/fetch <경로>",  icon: FaFileDownload, color: C.blue,   desc: "서버 파일 → Slack 전송\n폴더는 zip 압축 후 자동 전송" },
      { cmd: "/ls <경로>",     icon: FaSearch,       color: "7B1FA2", desc: "공유폴더 목록 조회\n파일 크기·타입 표시" },
      { cmd: "/cd  /pwd",      icon: FaFolder,       color: C.orange, desc: "디렉토리 이동 & 현재 위치 확인\n사용자별 독립 경로 유지" },
      { cmd: "/create <폴더>", icon: FaCog,          color: C.gray,   desc: "새 폴더 생성\n안전한 폴더명 정규식 검증" },
    ];

    for (let i = 0; i < features.length; i++) {
      const row = Math.floor(i / 3);
      const col = i % 3;
      const x = 0.3 + col * 3.15;
      const y = 0.95 + row * 2.15;
      const w = 2.9, h = 1.95;

      sl.addShape(pres.shapes.RECTANGLE, {
        x, y, w, h, fill: { color: C.white },
        shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.1 }
      });
      sl.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 0.1, h,
        fill: { color: features[i].color }, line: { color: features[i].color }
      });

      const ic = await iconPng(features[i].icon, "#FFFFFF", 256);
      sl.addShape(pres.shapes.OVAL, {
        x: x + 0.15, y: y + 0.15, w: 0.55, h: 0.55,
        fill: { color: features[i].color }, line: { color: features[i].color }
      });
      sl.addImage({ data: ic, x: x + 0.21, y: y + 0.21, w: 0.43, h: 0.43 });

      sl.addText(features[i].cmd, {
        x: x + 0.75, y: y + 0.1, w: 2.05, h: 0.45,
        fontSize: 13, bold: true, color: features[i].color,
        fontFace: "Consolas", margin: 0
      });
      sl.addText(features[i].desc, {
        x: x + 0.75, y: y + 0.55, w: 2.05, h: 1.25,
        fontSize: 11, color: C.text, lineSpacingMultiple: 1.3
      });
    }

  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 5 — 중복 파일 처리 흐름
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    addHeader(sl, "04  중복 파일 처리 & 상태 관리");

    // 왼쪽: 중복 처리 흐름
    sl.addText("중복 파일 처리 흐름", {
      x: 0.3, y: 0.9, w: 4.5, h: 0.4,
      fontSize: 14, bold: true, color: C.blue
    });

    const steps = [
      { label: "파일 업로드 + save 명령", color: C.blue },
      { label: "서버 경로에 동일 파일명 존재?", color: C.orange, decision: true },
      { label: "Slack 버튼 프롬프트 전송", color: "7B1FA2" },
    ];
    const actions = [
      { label: "덮어쓰기", color: C.red },
      { label: "새 이름으로 저장\n(타임스탬프 추가)", color: C.teal },
      { label: "취소", color: C.gray },
    ];

    steps.forEach((s, i) => {
      if (s.decision) {
        sl.addShape(pres.shapes.RECTANGLE, {
          x: 0.4, y: 1.35 + i * 0.85, w: 4.1, h: 0.55,
          fill: { color: C.orange, transparency: 80 }, line: { color: C.orange }
        });
      } else {
        sl.addShape(pres.shapes.RECTANGLE, {
          x: 0.4, y: 1.35 + i * 0.85, w: 4.1, h: 0.55,
          fill: { color: s.color, transparency: 85 }, line: { color: s.color }
        });
      }
      sl.addText(s.label, {
        x: 0.4, y: 1.35 + i * 0.85, w: 4.1, h: 0.55,
        fontSize: 12, bold: true, color: s.color, align: "center", valign: "middle"
      });
      if (i < steps.length - 1) {
        sl.addText("▼", { x: 2.1, y: 1.9 + i * 0.85, w: 0.7, h: 0.25,
          fontSize: 14, color: C.gray, align: "center" });
      }
    });

    actions.forEach((a, i) => {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 0.3 + i * 1.45, y: 4.0, w: 1.3, h: 0.7,
        fill: { color: a.color, transparency: 80 }, line: { color: a.color }
      });
      sl.addText(a.label, {
        x: 0.3 + i * 1.45, y: 4.0, w: 1.3, h: 0.7,
        fontSize: 10, bold: true, color: a.color, align: "center", valign: "middle"
      });
    });
    sl.addText("사용자 선택", { x: 0.3, y: 3.73, w: 4.2, h: 0.3,
      fontSize: 11, color: C.gray, align: "center" });

    // 구분선
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 4.85, y: 0.85, w: 0.03, h: 4.45,
      fill: { color: "CFD8DC" }, line: { color: "CFD8DC" }
    });

    // 오른쪽: 상태 관리
    sl.addText("상태 관리 구조", {
      x: 5.0, y: 0.9, w: 4.7, h: 0.4,
      fontSize: 14, bold: true, color: C.blue
    });

    const stateItems = [
      { key: "channel_dirs", desc: "사용자별 현재 디렉토리\n{channel_id}:{user_id} → 경로", color: C.teal },
      { key: "pending_saves", desc: "중복 처리 대기 중인 파일\n10분 TTL, 자동 만료 정리", color: "7B1FA2" },
      { key: "state.json", desc: "재시작해도 상태 유지\nDocker Volume 마운트", color: C.blue },
    ];

    stateItems.forEach((item, i) => {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 5.0, y: 1.35 + i * 1.1, w: 4.7, h: 0.9,
        fill: { color: C.white },
        shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 }
      });
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 5.0, y: 1.35 + i * 1.1, w: 0.08, h: 0.9,
        fill: { color: item.color }, line: { color: item.color }
      });
      sl.addText(item.key, {
        x: 5.15, y: 1.35 + i * 1.1, w: 4.4, h: 0.35,
        fontSize: 13, bold: true, color: item.color, fontFace: "Consolas", valign: "middle"
      });
      sl.addText(item.desc, {
        x: 5.15, y: 1.7 + i * 1.1, w: 4.4, h: 0.5,
        fontSize: 11, color: C.text, lineSpacingMultiple: 1.2
      });
    });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 6 — 보안 점검 개요
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    addHeader(sl, "05  보안 취약점 분석 — 3회 독립 점검", C.red);

    sl.addText("총 12개 취약점 발견 및 전부 수정 완료", {
      x: 0.3, y: 0.9, w: 9.4, h: 0.4,
      fontSize: 15, color: C.gray, italic: true
    });

    const passes = [
      {
        pass: "1차 점검", focus: "인증 · 접근 제어", color: C.red,
        items: [
          "버튼 클릭 user_id 검증 없음 → 타인이 덮어쓰기 가능",
          "/save 가 타인 파일 저장 가능",
          "_save_state() 읽기/쓰기 Race Condition",
        ]
      },
      {
        pass: "2차 점검", focus: "동시성 · 스레드 안전성", color: C.orange,
        items: [
          "공유 딕셔너리 무락(no-lock) 접근",
          "동일 파일 동시 저장 시 덮어씀",
          "cleanup 스레드 예외로 조용히 종료",
          "cleanup 비원자적 pop 시퀀스",
        ]
      },
      {
        pass: "3차 점검", focus: "운영 · 신뢰성", color: C.yellow,
        items: [
          "state.json Docker Volume 미마운트",
          "Rate Limiting 없음 (DoS 가능)",
          "/fetch 파일 수 · 크기 제한 없음",
          "/ls 대형 폴더 전체 메모리 로드",
        ]
      },
    ];

    passes.forEach((p, i) => {
      const x = 0.25 + i * 3.2;
      sl.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.35, w: 3.05, h: 3.8,
        fill: { color: C.white },
        shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.1 }
      });
      sl.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.35, w: 3.05, h: 0.7,
        fill: { color: p.color }, line: { color: p.color }
      });
      sl.addText(p.pass, {
        x: x + 0.1, y: 1.35, w: 2.85, h: 0.35,
        fontSize: 14, bold: true, color: C.white, valign: "middle", margin: 0
      });
      sl.addText(p.focus, {
        x: x + 0.1, y: 1.7, w: 2.85, h: 0.32,
        fontSize: 10, color: "FFE082", italic: true, valign: "middle", margin: 0
      });

      p.items.forEach((item, j) => {
        sl.addShape(pres.shapes.RECTANGLE, {
          x: x + 0.15, y: 2.15 + j * 0.71, w: 0.1, h: 0.42,
          fill: { color: p.color, transparency: 30 }, line: { color: p.color }
        });
        sl.addText(item, {
          x: x + 0.35, y: 2.15 + j * 0.71, w: 2.55, h: 0.55,
          fontSize: 10.5, color: C.text, lineSpacingMultiple: 1.2
        });
      });
    });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 7 — 수정 내역 상세
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    addHeader(sl, "06  취약점 수정 내역 (12/12 완료)", C.green);

    const fixes = [
      { id: "A1", sev: "Critical", issue: "버튼 user_id 검증 없음",    fix: "_UNAUTHORIZED sentinel 도입, 요청자만 버튼 처리", color: C.red },
      { id: "A2", sev: "Critical", issue: "/save 타인 파일 저장",       fix: "명령 실행자 파일만 히스토리 필터링",              color: C.red },
      { id: "A3", sev: "High",     issue: "_save_state Race Condition", fix: "스냅샷을 lock 안에서 읽고, I/O는 lock 밖 실행",  color: C.orange },
      { id: "B1", sev: "High",     issue: "딕셔너리 무락 접근",         fix: "_data_lock으로 모든 공유 상태 접근 보호",         color: C.orange },
      { id: "B2", sev: "Medium",   issue: "cleanup 비원자적 pop",       fix: "_cleanup_expired_locked() 내부 함수 분리",       color: C.yellow },
      { id: "B3", sev: "High",     issue: "cleanup 스레드 조용한 종료", fix: "try/except로 예외 포착, 스레드 영구 유지",        color: C.orange },
      { id: "B4", sev: "Medium",   issue: "동시 동일 파일 덮어씀",      fix: "_in_progress_paths 집합으로 경로 선점",          color: C.yellow },
      { id: "C1", sev: "High",     issue: "state.json 재시작 시 소실",  fix: "Docker Volume 마운트 (./data:/app/data)",        color: C.orange },
      { id: "C2", sev: "High",     issue: "Rate Limiting 없음 (DoS)",   fix: "_check_rate_limit() — 명령어별 cooldown 적용",   color: C.orange },
      { id: "C3", sev: "Medium",   issue: "/ls 전체 메모리 로드",       fix: "itertools.islice로 200개 제한 후 정렬",          color: C.yellow },
      { id: "C4", sev: "Low",      issue: "state.json 평문 권한",       fix: "os.chmod(600) 소유자만 읽기/쓰기",              color: "78909C" },
      { id: "C5", sev: "Low",      issue: "비원자적 파일 쓰기",         fix: ".tmp 임시 파일 후 atomic rename",               color: "78909C" },
    ];

    // 헤더행
    const hx = [0.25, 0.7, 1.35, 4.5];
    const hw = [0.42, 0.62, 3.1, 5.2];
    const headers = ["ID", "심각도", "발견된 문제", "수정 방법"];
    headers.forEach((h, i) => {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: hx[i], y: 0.88, w: hw[i], h: 0.32,
        fill: { color: "1A2744" }, line: { color: "1A2744" }
      });
      sl.addText(h, { x: hx[i], y: 0.88, w: hw[i], h: 0.32,
        fontSize: 10, bold: true, color: C.white, align: "center", valign: "middle" });
    });

    fixes.forEach((f, i) => {
      const y = 1.22 + i * 0.35;
      const bg = i % 2 === 0 ? C.white : "F8FAFC";
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 0.25, y, w: 9.45, h: 0.33,
        fill: { color: bg }, line: { color: "E0E0E0" }
      });
      sl.addText(f.id, { x: hx[0], y, w: hw[0], h: 0.33,
        fontSize: 10, bold: true, color: f.color, align: "center", valign: "middle", fontFace: "Consolas" });
      sl.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: hx[1] + 0.05, y: y + 0.04, w: hw[1] - 0.1, h: 0.25,
        fill: { color: f.color, transparency: 80 }, line: { color: f.color }, rectRadius: 0.04
      });
      sl.addText(f.sev, { x: hx[1], y, w: hw[1], h: 0.33,
        fontSize: 9, bold: true, color: f.color, align: "center", valign: "middle" });
      sl.addText(f.issue, { x: hx[2] + 0.05, y, w: hw[2] - 0.05, h: 0.33,
        fontSize: 10, color: C.text, valign: "middle" });
      sl.addText(f.fix, { x: hx[3] + 0.05, y, w: hw[3] - 0.05, h: 0.33,
        fontSize: 10, color: C.gray, valign: "middle" });
    });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 8 — 인프라 & 배포
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    addHeader(sl, "07  인프라 구성 & 배포");

    // 왼쪽: 배포 흐름
    sl.addText("배포 흐름", {
      x: 0.3, y: 0.9, w: 4.5, h: 0.38,
      fontSize: 14, bold: true, color: C.blue
    });

    const deploySteps = [
      { step: "1", label: "코드 수정 (로컬 맥북)", sub: "app.py, docker-compose.yml", color: C.blue },
      { step: "2", label: "rsync 전송", sub: "yangzepa@100.127.64.21", color: C.teal },
      { step: "3", label: "docker compose up --build", sub: "서버에서 컨테이너 재빌드", color: "7B1FA2" },
      { step: "4", label: "Slack Socket Mode 연결", sub: "WebSocket 세션 수립 완료", color: C.green },
    ];

    deploySteps.forEach((s, i) => {
      sl.addShape(pres.shapes.OVAL, {
        x: 0.35, y: 1.38 + i * 0.9, w: 0.45, h: 0.45,
        fill: { color: s.color }, line: { color: s.color }
      });
      sl.addText(s.step, { x: 0.35, y: 1.38 + i * 0.9, w: 0.45, h: 0.45,
        fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle" });
      if (i < deploySteps.length - 1) {
        sl.addShape(pres.shapes.RECTANGLE, {
          x: 0.54, y: 1.83 + i * 0.9, w: 0.08, h: 0.45,
          fill: { color: "CFD8DC" }, line: { color: "CFD8DC" }
        });
      }
      sl.addText(s.label, {
        x: 0.9, y: 1.38 + i * 0.9, w: 3.8, h: 0.28,
        fontSize: 13, bold: true, color: s.color, valign: "middle", margin: 0
      });
      sl.addText(s.sub, {
        x: 0.9, y: 1.65 + i * 0.9, w: 3.8, h: 0.22,
        fontSize: 10, color: C.gray, margin: 0
      });
    });

    // 구분선
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 4.85, y: 0.85, w: 0.03, h: 4.45,
      fill: { color: "CFD8DC" }, line: { color: "CFD8DC" }
    });

    // 오른쪽: 기술 스택
    sl.addText("기술 스택", {
      x: 5.0, y: 0.9, w: 4.7, h: 0.38,
      fontSize: 14, bold: true, color: C.blue
    });

    const techStack = [
      ["언어",    "Python 3.11",               C.blue],
      ["Slack",   "Bolt SDK + Socket Mode",     "4A154B"],
      ["인프라",  "Docker + docker-compose",    "0288D1"],
      ["네트워크","Tailscale VPN",              C.teal],
      ["파일공유","Samba (ecsamba)",            C.orange],
      ["동시성",  "threading.Lock + 데몬 스레드", C.gray],
    ];

    techStack.forEach(([cat, val, color], i) => {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 5.0, y: 1.35 + i * 0.62, w: 1.3, h: 0.48,
        fill: { color, transparency: 85 }, line: { color }
      });
      sl.addText(cat, { x: 5.0, y: 1.35 + i * 0.62, w: 1.3, h: 0.48,
        fontSize: 11, bold: true, color, align: "center", valign: "middle" });
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 6.35, y: 1.35 + i * 0.62, w: 3.35, h: 0.48,
        fill: { color: C.white }, line: { color: "E0E0E0" }
      });
      sl.addText(val, { x: 6.4, y: 1.35 + i * 0.62, w: 3.25, h: 0.48,
        fontSize: 12, color: C.text, valign: "middle" });
    });
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // 슬라이드 9 — 마무리
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };

    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 0.18, h: 5.625,
      fill: { color: C.teal }, line: { color: C.teal }
    });

    sl.addText("한계 & 향후 개선 방향", {
      x: 0.4, y: 0.5, w: 9.2, h: 0.55,
      fontSize: 28, bold: true, color: C.white, fontFace: "Arial Black", margin: 0
    });

    const limits = [
      { icon: FaLock, title: "권한 시스템 미구현",
        desc: "모든 채널 멤버가 동등한 권한\n관리자 / 일반 사용자 구분 없음" },
      { icon: FaBug, title: "Slack-CMS 연동 예정",
        desc: "파일 메타데이터 관리\n태그·검색 기능 추가 계획" },
      { icon: MdSpeed, title: "알림 기능",
        desc: "공유폴더 파일 변경 감지\nSlack 자동 알림 예정" },
    ];

    for (let i = 0; i < limits.length; i++) {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 0.4 + i * 3.15, y: 1.15, w: 2.95, h: 3.2,
        fill: { color: "0D2137" }, line: { color: C.teal }
      });
      const ic = await iconPng(limits[i].icon, "#00897B", 256);
      sl.addImage({ data: ic, x: 1.45 + i * 3.15, y: 1.35, w: 0.75, h: 0.75 });
      sl.addText(limits[i].title, {
        x: 0.45 + i * 3.15, y: 2.2, w: 2.85, h: 0.45,
        fontSize: 14, bold: true, color: "00BCD4", align: "center"
      });
      sl.addText(limits[i].desc, {
        x: 0.45 + i * 3.15, y: 2.75, w: 2.85, h: 1.4,
        fontSize: 12, color: "90A4AE", align: "center", lineSpacingMultiple: 1.4
      });
    }

    sl.addText("File Gateway — 연구실 파일 관리를 Slack 하나로", {
      x: 0.4, y: 4.7, w: 9.2, h: 0.45,
      fontSize: 13, color: "546E7A", align: "center", italic: true
    });
  }

  const outPath = "/Users/home/Desktop/나만의무언가/file move/FileGateway_Presentation.pptx";
  await pres.writeFile({ fileName: outPath });
  console.log("✅ 저장 완료:", outPath);
}

buildPptx().catch(e => { console.error(e); process.exit(1); });
