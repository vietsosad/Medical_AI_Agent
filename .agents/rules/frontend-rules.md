# ⚡ FRONTEND ENGINEERING RULES & TECH STACK (AI PROMPT INCLUSION FILE)
*(File đặc tả luật kỹ thuật & Tech stack cho Frontend - Đính kèm tài liệu này mỗi khi yêu cầu AI viết code Giao diện)*

Tài liệu này xác định **quy chuẩn công nghệ bắt buộc (Mandatory Tech Stack)**, **cấu trúc thư mục (Folder Structure)** và **quy ước viết mã (Coding Rules)** cho phần Frontend. Khi lập trình, Trợ lý AI và Kỹ sư **BẮT BUỘC** tuân thủ tuyệt đối cấu trúc này, không bàn luận hay tự ý thay thế bằng các công nghệ khác.

---

## 1. MỘT SỐ BẮT BUỘC (MANDATORY TECH STACK)

| Nhóm Công Nghệ | Thư Viện / Framework Chuẩn | Phạm Vi & Mục Đích Sử Dụng |
| :--- | :--- | :--- |
| **Core Framework** | **Next.js 15 (App Router)** | Rendering chính, Server Actions, SSR & Streaming, Tối ưu SEO và hiệu suất tải trang. |
| **Language** | **TypeScript 5.x** | Bắt buộc **Strict Mode**. Tuần tự hóa kiểu dữ liệu 100% (Từ chối `any`). |
| **Styling Engine** | **Tailwind CSS v4** | Sử dụng CSS Variables và utility classes mới nhất. Tích hợp bộ gộp class `cn()` (clsx + tailwind-merge). |
| **UI Primitives** | **shadcn/ui** (+ Radix UI) | Tái sử dụng base components dạng mở (Button, Dialog, Sheet, Popover...) tại `src/components/ui/`, hỗ trợ chuẩn accessibility (WAI-ARIA). |
| **Server State** | **TanStack Query (React Query v5)** | Quản lý cache dữ liệu API, đồng bộ Realtime, invalidation, polling và Optimistic UI Updates cho mọi kết nối tới FastAPI Backend. |
| **Client State** | **Zustand** | Quản lý state thuần Giao diện (UI State): Trạng thái mở modal SOS, dark mode, thanh trình khám, lọc hàng đợi, hay drawer toggle. |
| **Forms & Validation** | **React Hook Form + Zod** | Kiểm soát 100% các biểu mẫu đầu vào (Form khai báo, Questionnaire trắc nghiệm, ghi chú Override của Bác sĩ) kết hợp xác minh runtime với Zod schema. |
| **Animations & UI** | **Motion (Framer Motion)** | Animation mượt mà cho chuyên trang, transition khi mở Modal khẩn cấp, hiệu ứng chớp tim (pulse/ping) cho Red-Flag <50ms. |
| **Data Visualization** | **Recharts** | Hiển thị biểu đồ thống kê KPI, Concordance Rate, và phân tích số liệu trên Dashboard cho Bác Sĩ & Admin. |
| **Tables & Grids** | **TanStack Table v8** | Quản lý bảng biểu Headless cho danh sách bệnh nhân, hàng đợi Triage ESI, lịch hẹn lâm sàng và nhật ký kiểm toán Audit Logs. |

---

## 2. CẤU TRÚC THƯ MỰC CHUẨN (FOLDER STRUCTURE)

Mọi mã nguồn Frontend phải nằm bên trong thư mục `src/` tuân theo kiến trúc Separation of Concerns (Phân định Trách nhiệm Rõ ràng):

```text
frontend/src/
├── app/                  # Next.js 15 App Router (Pages, Layouts, Loading, Error Boundaries)
│   ├── (auth)/           # Route group cho Đăng ký / Đăng nhập / Guest Bypass
│   ├── (patient)/        # Route group cho Cổng tương tác Bệnh nhân & Lịch sử chat
│   ├── (clinical)/       # Route group cho Dashboard Điều Dưỡng & HITL Workspace
│   ├── (admin)/          # Route group cho Quản trị viên & Analytics Charts
│   ├── layout.tsx        # Global App Root Layout
│   └── globals.css       # Cấu hình Tailwind CSS v4 variables & clinical colors
│
├── components/           # Tự viện React Components
│   ├── ui/               # Nguyên bản shadcn/ui components (button, dialog, input, card...)
│   ├── shared/           # Components dùng chung (Navbar, Sidebar, Floating SOS Button, Skeleton)
│   ├── chat/             # Components cho Trợ lý Triage (Chat window, trắc nghiệm choice pills)
│   ├── clinical/         # Components cho Bác sĩ (Kanban Queue, SBAR Handoff Card, RAG Citations)
│   └── charts/           # Components biểu đồ thống kê dùng Recharts
│
├── hooks/                # Custom React Hooks phục vụ logic thao tác DOM/Giao diện
├── lib/                  # Tiện ích chung (hàm `cn()`, Axios/Fetch client, TanStack Query client init)
├── queries/              # TanStack Query Hooks (`useQuery`, `useMutation`) & Query Keys wrapping API endpoints
├── schemas/              # Zod validation schemas & TypeScript runtime validation logic
├── store/                # Zustand UI State stores (`useUIStore`, `useTriageState`, `useFilterStore`)
└── types/                # TypeScript interfaces / DTO contracts dùng toàn app
```

---

## 3. QUY ƯỚC LẬP TRÌNH & NGUYÊN TẮC KỸ THUẬT (ENGINEERING COMMANDMENTS)

### 3.1. Phân định Ranh giới Server Component vs Client Component (RSC Rules)
*   **Mặc định là Server Components:** Không được khai báo `"use client";` ở các trang Layout hoặc Page container trên cùng nếu không thật sự cần thiết.
*   **Chỉ áp dụng `"use client";` ở Leaf Components (Component Lá) khi có các yếu tố sau:**
    *   Sử dụng React Hooks (`useState`, `useEffect`, `useCallback`, `useRef`).
    *   Gắn sự kiện người dùng (`onClick`, `onChange`, `onSubmit`).
    *   Tích hợp TanStack Query Hooks (`useQuery`, `useMutation`), Zustand stores, biểu đồ Recharts, bảng TanStack Table hoặc animation của Motion.

### 3.2. Ranh giới Quản lý Trạng thái (State Management Boundaries)
*   🚫 **KHÔNG DÙNG ZUSTAND để lưu trữ hay cache dữ liệu API từ Backend trả về.** (Nhiệm vụ này thuộc về **TanStack Query**).
*   ✅ **ZUSTAND chỉ dành cho UI State & Client Session State:** Trạng thái ẩn/hien Sidebar, bộ lọc bảng khám tạm thời, bước hiện tại của Thanh tiến trình Khai báo, hoặc kích hoạt cờ Báo động đỏ toàn màn hình (Overlay Trigger).

### 3.3. Viết Mã Styling & UI Components (Shadcn + Tailwind v4 Rules)
*   **Quy tắc Phân Bổ Màu Lâm Sàng 60 - 30 - 10 (MANDATORY COLOR SPATIAL RULE):**
    *   Trước khi viết hay tái cấu trúc bất kỳ component Giao diện nào, Agent **BẮT BUỘC** phải tuân thủ quy chuẩn không gian màu 60-30-10: **60%** Màu Chủ đạo (Primary neutral background), **30%** Màu Thứ cấp (Secondary structure/navbar/cards/header), **10%** Màu Điểm xuyết (Accent/CTA buttons/icons/progress thu hút thị giác nhất để dẫn dắt hành động).
    *   **Bắt buộc sử dụng 1 trong 3 Theme Màu Xanh Dương Lâm Sàng (Clinical Trust Blue - Brand Anchor):**
        1. **Pristine Day Medical (Ban ngày / Cổng Triage Bệnh nhân):** Nền Trắng/Slate-50 dịu mắt (60%), Thẻ Card/Navbar Slate-100/Navy (30%), Nút CTA Xanh Sky-600/Blue-600 (10%).
        2. **Deep Slate Night ER (Cấp cứu Ca Trực Đêm / Điều dưỡng HITL):** Nền Slate-950/Zinc-950 sâu thẳm (60%), Thẻ Card Slate-900 (30%), Nút CTA & Cờ RAG Xanh Sáng Sky-400/Sky-500 & Rose Alarm (10%), triệt tiêu hoàn toàn mỏi mắt cho ca trực ban đêm.
        3. **Pediatric & Family Serenity (Chăm sóc Gia đình / Nhi khoa & Thai Phụ):** Nền Xanh Nhạt dịu Sky-50/30 (60%), Thẻ Card Trắng ngọc bo nhẵn mượt (30%), Nút CTA Teal-600/Cyan mượt ấm áp, an tâm (10%).
    *   **Quy chuẩn Màu Trạng Thái Giao Tiếp Bắt Buộc cho Giao Diện Sáng (MANDATORY SEMANTIC COLORS FOR LIGHT UI):**
        *   **Xanh lá (Success - Green / Emerald):** Báo thành công, ký nhận khám hoàn tất hoặc sinh hiệu bình ổn (`bg-emerald-50 text-emerald-800 border-emerald-200` hoặc nút `bg-emerald-600 text-white`).
        *   **Đỏ (Error / Danger / Emergency - Red / Rose):** Báo lỗi biểu mẫu, cảnh báo nguy hiểm lâm sàng ESI 1, còi báo động hoặc hành động xóa bỏ dữ liệu nhạy cảm (`bg-rose-600 hover:bg-rose-700 text-white font-bold` hoặc cảnh báo tĩnh `bg-rose-50 text-rose-800 border-rose-200`).
        *   **Vàng / Cam (Warning - Yellow / Amber / Orange):** Cảnh báo cần chú ý, vi phạm hạn giờ xử lý SLA hoặc ESI 2 ranh giới (`bg-amber-50 text-amber-900 border-amber-300`).
        *   **Xanh dương (Info / AI Intelligence - Blue / Sky):** Thông tin bổ sung, trích lục suy luận AI SBAR và căn cứ phác đồ RAG (`bg-sky-50 text-sky-900 border-sky-200` hoặc nút `bg-sky-600 text-white`).
*   **Bắt buộc dùng `cn()`:** Khi kết hợp Tailwind classes hay phó mặc cho props từ bên ngoài truyền vào, tuyệt đối phải sử dụng utility `cn(clsx + tailwind-merge)` nhằm cấm xung đột class:
    ```tsx
    import { cn } from "@/lib/utils";
    // Ví dụ cú pháp bắt buộc:
    <div className={cn("p-4 rounded-xl bg-zinc-900 border border-zinc-800", className)}>
    ```
*   **Iconography (Biểu Tượng & Vector Icons):** 
    *   🚫 **TUYỆT ĐỐI CẤM SỬ DỤNG ICON DẠNG TEXT / EMOJI TRONG GIAO DIỆN (NO TEXT/EMOJI ICONS IN UI):** Không bao giờ được sử dụng các biểu tượng dạng ký tự text hay emoji (ví dụ: 🛡️, 🚨, 🔐, ⚡, 🔥, ✨, 🩺, v.v.) bên trong văn bản giao diện, nút bấm (Button), nhãn mác (Badge) hay thẻ UI vì trông rất thiếu chuyên nghiệp và lệch chuẩn giữa các hệ điều hành/trình duyệt.
    *   ✅ **BẮT BUỘC BẰNG THƯ VIỆN CHUẨN:** 100% biểu tượng trong ứng dụng phải là icon vector từ thư viện `lucide-react` hoặc ảnh SVG thiết kế chuẩn y khoa. Đảm bảo kích cỡ chuẩn (`w-4 h-4` cho nút nhỏ, `w-5 h-5` cho action chính, `w-6 h-6+` cho các cảnh báo ESI Level) và hiệu ứng thị giác chuyên sâu.

### 3.4. Xử lý Dữ liệu Bảng Biểu & Biểu Đồ (Tables & Charts)
*   **Bảng Bệnh nhân & Hàng đợi (TanStack Table v8):** Khi tạo bảng danh sách ca lâm sàng, phải khai báo trọn vẹn Column Definitions mang tính type-safe, tích hợp tính năng sắp xếp theo mức ưu tiên ESI (1 ➔ 5) và lọc theo trạng thái HITL.
*   **Biểu Đồ Thống Kê (Recharts):** Wrap mọi component Recharts bên trong `<ResponsiveContainer width="100%" height={300}>` và lazy-load hoặc bọc trong Client Component để không gây xung đột SSR Hydro mismatch.

### 3.5. Tiêu Chuẩn Xử Lý Biểu Mẫu (Forms & Zod Validation)
*   **100% Forms dùng React Hook Form + Zod:** Không dùng state lẻ tẻ (`onChange={e => SetName(...)}`) cho các form nhiều trường. Phải khai báo schema rõ ràng:
    ```tsx
    import { useForm } from "react-hook-form";
    import { zodResolver } from "@hookform/resolvers/zod";
    import * as z from "zod";

    const triageInputSchema = z.object({
      symptom_text: z.string().min(3, "Vui lòng mô tả ít nhất 3 ký tự."),
      selected_options: z.array(z.string()).optional(),
    });

    export type TriageFormValues = z.infer<typeof triageInputSchema>;
    ```

### 3.6. Tối Ưu Tốc Độ & Trợ Năng (Performance & WAI-ARIA)
*   **Trạng Thái Chế Đội (Skeleton Loaders):** Không để giao diện chớp trắng (White Flash). Luôn hiển thị Skeleton khi TanStack Query ở trạng thái `isLoading`.
*   **Danh Định Stable Keys:** Mọi vòng lặp `.map()` cho thẻ ca khám, lựa chọn trắc nghiệm hay mục lịch sử phải dùng UUID từ DB cho thuộc tính `key`. Tuyệt đối cấm dùng chỉ số `index` của mảng làm `key`.
*   **Thẻ ARIA:** Với các Notification hú còi ESI 1 hoặc cảnh báo Red-flag <50ms, bắt buộc gán thẻ `role="alert"` và `aria-live="assertive"`.

### 3.7. Hiến Pháp Thiết Kế Lâm Sàng Tối Thượng (UI Redesign System Mandatory Rules)
Mọi component trong hệ thống buộc phải tuần thủ 18 Bộ Luật Tối Cao từ [UI_REDESIGN_SYSTEM.md](file:///home/viet/Documents/vinAI/P-159/UI_REDESIGN_SYSTEM.md). Nếu vi phạm bất kỳ điều kiện nào bên dưới, mã nguồn bị loại bỏ tức khắc (**FAILED**):
1. **Clarity Over Beauty (Rõ ràng > Hào nhoáng):** Thiết kế phục vụ hiệu suất thao tác y khoa. Phải giảm thiểu tải nhận thức (Cognitive Load < 3 giây để nhận biết: Ai - Cái gì - Mức độ khẩn - Hành động ngay).
2. **Quy Luật Không Gian Lưới 8px (Strict 8px Spacing Grid):** Cấm hoàn toàn khoảng cách ngẫu hứng (`p-2.5`, `py-1`, `m-3`). Chỉ áp dụng các bội số của 8px: `8px (p-2/gap-2)`, `16px (p-4/gap-4)`, `24px (p-6/gap-6)`, `32px (p-8/gap-8)` để đảm bảo nhịp thở cho dữ liệu.
3. **Quy Chuẩn Kích Thước Chữ (Typography Scale):** 
   - **Nghiêm cấm font tí hon:** Không dùng `text-[9px]`, `text-[10px]`, `text-[11px]` cho bất kỳ nhãn dữ liệu thực thi nào.
   - **Body text:** Tối thiểu **14-16px (`text-sm / text-base`)**.
   - **Dữ liệu y khoa quan trọng (Tên ca, Mức độ ESI, Đồng hồ SLA):** Tối thiểu **16-20px (`text-base / text-lg / text-xl`)**, đọc rõ từ khoảng cách trực chiến.
4. **Quy Luật Cấu Trúc Thẻ (Card Rules - Zero Clutter):** Một thẻ Card (như Hàng Đợi Kanban) chỉ được bao hàm: Dữ liệu Sơ cấp -> Dữ liệu Thứ cấp -> **Đúng 1 nút Primary CTA duy nhất**. Nghiêm cấm tạo các hộp bo viền lồng hộp (No nested cards) và lạm dụng huy hiệu thừa thãi.
5. **Quy Luật Màu Sắc (Color Functional Only):** Tối đa 3 màu chính, 1 màu phụ trợ. Cấm dùng màu để trang trí cá nhân. Chỉ dùng màu phân định mức nguy nan: Đỏ (Critical / ESI 1) > Cam (Warning / ESI 2) > Xanh lá (Normal / ESI 4-5) > Xanh lam (Info / ESI 3/SBAR).
6. **Quy Trình Audit Trước Sửa Chuẩn QA (No Direct Rewrite):** Luôn phải lập Báo cáo Kiểm thử (Phase 1 Audit) & Thẩm định Lỗi vi phạm (Phase 2 Rule Validation) trước khi tiến hành viết lại code. Đảm bảo 12 tiêu chí nghiệm thu QA luôn **>= 95/100 điểm**.

---
*Hết Bộ Quy Chuẩn Kỹ Thuật Frontend Rules.*  
**Mọi mã nguồn Frontend xuất ra từ AI hay lập trình viên đều phải đối chiếu tuyệt đối với tài liệu này.**

