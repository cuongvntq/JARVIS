"use client";

import { api, setAccessToken } from "@/lib/api";
import { ApiException } from "@/lib/types/api";
import { useAuthStore } from "@/stores/authStore";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

const schema = z
  .object({
    name: z.string().min(1, "Vui lòng nhập tên").max(100),
    email: z.string().email("Email không hợp lệ"),
    password: z
      .string()
      .min(8, "Mật khẩu tối thiểu 8 ký tự")
      .regex(/(?=.*[A-Za-z])(?=.*\d)/, "Phải có ít nhất 1 chữ cái và 1 chữ số"),
    confirmPassword: z.string(),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "Mật khẩu không khớp",
    path: ["confirmPassword"],
  });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
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
      const resp = await api.register({
        email: data.email,
        password: data.password,
        name: data.name,
      });
      setAccessToken(resp.access_token);
      setAuth(resp.user, resp.access_token);
      router.replace("/");
    } catch (e) {
      if (e instanceof ApiException) {
        if (e.error.code === "email_taken") {
          setErrorMsg("Email này đã được sử dụng");
        } else if (e.error.code === "weak_password") {
          setErrorMsg(e.error.message);
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
            {...register("name")}
            placeholder="Tên của bạn"
            className="w-full rounded-lg border bg-transparent px-4 py-3 text-sm outline-none"
            style={{ borderColor: "rgba(0,180,216,0.2)", color: "#e2e8f0" }}
          />
          {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name.message}</p>}
        </div>

        <div>
          <input
            {...register("email")}
            type="email"
            placeholder="Email"
            className="w-full rounded-lg border bg-transparent px-4 py-3 text-sm outline-none"
            style={{ borderColor: "rgba(0,180,216,0.2)", color: "#e2e8f0" }}
          />
          {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>}
        </div>

        <div>
          <input
            {...register("password")}
            type="password"
            placeholder="Mật khẩu (tối thiểu 8 ký tự, có chữ và số)"
            className="w-full rounded-lg border bg-transparent px-4 py-3 text-sm outline-none"
            style={{ borderColor: "rgba(0,180,216,0.2)", color: "#e2e8f0" }}
          />
          {errors.password && (
            <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>
          )}
        </div>

        <div>
          <input
            {...register("confirmPassword")}
            type="password"
            placeholder="Nhập lại mật khẩu"
            className="w-full rounded-lg border bg-transparent px-4 py-3 text-sm outline-none"
            style={{ borderColor: "rgba(0,180,216,0.2)", color: "#e2e8f0" }}
          />
          {errors.confirmPassword && (
            <p className="mt-1 text-xs text-red-400">{errors.confirmPassword.message}</p>
          )}
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
          style={{
            backgroundColor: "rgba(0,180,216,0.15)",
            color: "rgba(0,180,216,0.9)",
            border: "1px solid rgba(0,180,216,0.3)",
          }}
        >
          {isSubmitting ? "Đang tạo tài khoản..." : "ĐĂNG KÝ"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm" style={{ color: "#5e8a9e" }}>
        Đã có tài khoản?{" "}
        <Link href="/auth/login" style={{ color: "rgba(0,180,216,0.7)" }}>
          Đăng nhập
        </Link>
      </p>
    </>
  );
}
