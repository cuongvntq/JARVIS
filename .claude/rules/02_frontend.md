# Rules — Frontend (Next.js 15 / TypeScript)

## UI Architecture

- **Reuse components:** trước khi tạo component mới, tìm trong `components/` xem đã có chưa.
- **Prefer composition:** truyền `children` / slot pattern thay vì tạo nhiều variant prop phức tạp.
- **Keep state local:** state chỉ nâng lên (lift up) khi thực sự cần share. Không đưa vào Zustand nếu chỉ dùng trong 1 component.
- **Avoid prop drilling:** nếu truyền prop qua 3+ level, dùng Tanstack Query cache hoặc Zustand thay vì tiếp tục drill.
- **Server Components when possible:** data fetching trên server giảm bundle size và waterfall.

## Component Model

- **Server Components mặc định** — chỉ thêm `"use client"` khi component cần: event handler, React hooks, browser API (localStorage, window, ...).
- Không fetch data trong Client Component bằng `useEffect` + `fetch` — dùng Tanstack Query.
- Tổ chức: `app/` cho routing/layout, `components/` cho UI tái dùng, `lib/` cho utils/helpers.

## Data Fetching

- Mọi API call đều qua **Tanstack Query** (`useQuery`, `useMutation`). Không raw `fetch` trong component.
- Tạo custom hooks trong `lib/hooks/` (ví dụ `useTodos`, `useNotes`) — không inline query trong component.
- Key format: `['todos', filter]`, `['todo', id]` — nhất quán để invalidate đúng cache.
- Sau mutation thành công: `queryClient.invalidateQueries({ queryKey: ['todos'] })`.

## Chat & Streaming

- Chat streaming dùng **Vercel AI SDK** `useChat` hook — không tự xử lý SSE thủ công.
- Stream endpoint của backend: `POST /v1/chat/send` với `stream: true`.

## Datetime Display

- **Luôn dùng user timezone** khi hiển thị datetime — lấy từ Zustand user store.
- Dùng **date-fns** với `formatInTimeZone` (từ `date-fns-tz`). Không dùng `new Date().toLocaleString()` trực tiếp.
- Format Việt: `"HH:mm dd/MM/yyyy"` hoặc `"HH:mm 'hôm nay'"` theo context.

## Forms

- Form validation dùng **react-hook-form** + **zod** schema. Không uncontrolled form cho form phức tạp.
- Zod schema đặt trong `lib/schemas/` để tái dùng giữa form và API type guard.

## State Management

- **Zustand** cho global state ít thay đổi: user profile, theme, notification permission.
- Tanstack Query cache là source of truth cho server data — không copy server data vào Zustand.
- Không dùng Context API cho state thay đổi thường xuyên (gây re-render toàn tree).

## Styling

- Dùng **Tailwind CSS** utility classes. Không viết CSS file riêng trừ `globals.css`.
- Component phức tạp dùng **shadcn/ui** làm base — customize qua `className` prop.
- Responsive: mobile-first (`sm:`, `md:`, `lg:`).

## TypeScript

- Không dùng `any`. Nếu không biết type, dùng `unknown` rồi narrow.
- API response types đặt trong `lib/types/api.ts` — tạo từ OpenAPI spec hoặc viết tay theo docs/02.
- Import alias: `@/*` cho `src/*`.

## Linting & Format

- **Biome** xử lý cả lint + format (thay ESLint + Prettier). Chạy `pnpm lint` trước commit.
- Không disable biome rule trừ khi có lý do cụ thể và comment giải thích.
