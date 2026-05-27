"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { api, setAccessToken } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { ApiException } from "@/lib/types/api";

const schema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(1, "Vui lòng nhập mật khẩu"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [errorMsg, setErrorMsg] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setErrorMsg("");
    try {
      const resp = await api.login(data);
      setAccessToken(resp.access_token);
      setAuth(resp.user, resp.access_token);
      router.replace("/");
    } catch (e) {
      if (e instanceof ApiException) {
        if (e.error.code === "invalid_credentials") {
          setErrorMsg("Email hoặc mật khẩu không đúng");
        } else if (e.error.code === "account_disabled") {
          setErrorMsg("Tài khoản đã bị vô hiệu hóa");
        } else {
          setErrorMsg(e.error.message);
        }
      } else {
        setErrorMsg("Không thể kết nối đến máy chủ");
      }
    }
  };

  return (
    <>
      <h1
        className="mb-6 text-center text-2xl font-bold tracking-widest"
        style={{ fontFamily: "var(--font-orbitron)", color: "rgba(0,180,216,0.9)" }}
      >
        JARVIS
      </h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <input
            {...register("email")}
            type="email"
            placeholder="Email"
            className="w-full rounded-lg border bg-transparent px-4 py-3 text-sm outline-none transition"
            style={{ borderColor: "rgba(0,180,216,0.2)", color: "#e2e8f0" }}
          />
          {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>}
        </div>

        <div>
          <input
            {...register("password")}
            type="password"
            placeholder="Mật khẩu"
            className="w-full rounded-lg border bg-transparent px-4 py-3 text-sm outline-none transition"
            style={{ borderColor: "rgba(0,180,216,0.2)", color: "#e2e8f0" }}
          />
          {errors.password && <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>}
        </div>

        {errorMsg && (
          <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
            {errorMsg}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-lg py-3 text-sm font-semibold tracking-wider transition disabled:opacity-50"
          style={{ backgroundColor: "rgba(0,180,216,0.15)", color: "rgba(0,180,216,0.9)", border: "1px solid rgba(0,180,216,0.3)" }}
        >
          {isSubmitting ? "Đang đăng nhập..." : "ĐĂNG NHẬP"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm" style={{ color: "#5e8a9e" }}>
        Chưa có tài khoản?{" "}
        <Link href="/auth/register" style={{ color: "rgba(0,180,216,0.7)" }}>
          Đăng ký
        </Link>
      </p>
    </>
  );
}
