import { RouterProvider } from "react-router-dom";

import { router } from "@/app/router";
import { AuthSessionSync } from "@/components/auth/AuthSessionSync";

export default function App() {
  return (
    <>
      <AuthSessionSync />
      <RouterProvider router={router} />
    </>
  );
}
