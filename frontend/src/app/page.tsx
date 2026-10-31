import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.main}>
      <h1>Hackathon</h1>
      <p>Next.js + FastAPI 개발 환경</p>
      <p>백엔드를 실행한 뒤 아래 링크에서 API 응답을 확인하세요.</p>
      <a href="/api/health">API 상태 확인 →</a>
    </main>
  );
}
