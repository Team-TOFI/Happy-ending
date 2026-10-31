import { Suspense } from "react";
import { GoogleLoginScreen } from "@/components/tofi/auth";
export const metadata = { title: "Google 로그인" };
export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <p className="container loading-header">
          로그인 화면을 불러오고 있어요.
        </p>
      }
    >
      <GoogleLoginScreen />
    </Suspense>
  );
}
