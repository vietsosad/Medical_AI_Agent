"use client";

import React, { useCallback, useMemo, useState } from "react";
import { useForm, Controller, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion, AnimatePresence } from "framer-motion";
import {
  PhoneCall,
  UserPlus,
  Edit3,
  Trash2,
  ShieldAlert,
  Phone,
  User,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  X,
  ShieldCheck,
  AlertOctagon,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useEmergencyContacts } from "@/queries/use-clinical-profile";
import { useUpdateEmergencyContacts } from "@/queries/use-profile-mutations";
import {
  EmergencyContactSchema,
  type EmergencyContactFormValues,
} from "@/schemas/clinical-profile.schema";
import type { EmergencyContactDTO, RelationshipType } from "@/types/clinical-profile";
import { toast } from "sonner";

// ============================================================================
// 1. CONSTANTS FOR RELATIONSHIPS
// ============================================================================
const RELATIONSHIP_OPTIONS: Array<{ value: RelationshipType; label: string; icon?: React.ElementType }> = [
  { value: "SPOUSE", label: "Vợ / Chồng" },
  { value: "PARENT", label: "Cha / Mẹ" },
  { value: "CHILD", label: "Con cái" },
  { value: "SIBLING", label: "Anh / Chị / Em" },
  { value: "FRIEND", label: "Bạn bè / Đồng nghiệp" },
  { value: "OTHER", label: "Người thân khác" },
];

export interface EmergencySosManagerProps {
  className?: string;
}

/**
 * Trung Tâm Liên Hệ Khẩn Cấp SOS & Quản Lý Danh Bạ 115 (EmergencySosManager)
 * - Tối đa 3 thẻ, trong đó thẻ cờ is_primary === true là NGUỒN LIÊN HỆ CẤP CỨU SỐ 1
 *   với đường viền chớp chớp nhịp thở lộng lẫy và huy hiệu nổi bật.
 * - Thẩm mỹ: Chuẩn Y tế Hiện Đại Sáng Sủa (Pristine Bright Medical Theme).
 */
export const EmergencySosManager: React.FC<EmergencySosManagerProps> = ({ className }) => {
  const { data: contactsData, isLoading, isError, refetch } = useEmergencyContacts();
  const updateMutation = useUpdateEmergencyContacts();

  const contacts = useMemo(() => contactsData ?? [], [contactsData]);
  const isMaxReached = contacts.length >= 3;

  // State quản lý Dialog Thêm / Sửa
  const [isDialogOpen, setIsDialogOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // State quản lý AlertDialog xác nhận trước khi xóa người liên hệ Ưu Tiên 1
  const [contactToDelete, setContactToDelete] = useState<EmergencyContactDTO | null>(null);

  // React Hook Form cho 1 thẻ SOS
  const form = useForm<EmergencyContactFormValues>({
    resolver: zodResolver(EmergencyContactSchema),
    defaultValues: {
      full_name: "",
      relationship: "SPOUSE",
      phone_number: "",
      is_primary: contacts.length === 0, // Mặc định là số 1 nếu là thẻ đầu tiên
      address: "",
    },
  });

  // Mở modal thêm mới
  const handleOpenAdd = useCallback(() => {
    if (isMaxReached) {
      toast.warning("Đã đạt giới hạn tối đa 3 người liên hệ khẩn cấp.");
      return;
    }
    setEditingId(null);
    form.reset({
      full_name: "",
      relationship: "SPOUSE",
      phone_number: "",
      is_primary: contacts.length === 0 || !contacts.some((c) => c.is_primary),
      address: "",
    });
    setIsDialogOpen(true);
  }, [isMaxReached, contacts, form]);

  // Mở modal sửa
  const handleOpenEdit = useCallback(
    (contact: EmergencyContactDTO) => {
      setEditingId(contact.id || null);
      form.reset({
        full_name: contact.full_name,
        relationship: contact.relationship,
        phone_number: contact.phone_number,
        is_primary: contact.is_primary,
        address: contact.address || "",
      });
      setIsDialogOpen(true);
    },
    [form]
  );

  // Xử lý khi Submit Form
  const onSubmit: SubmitHandler<EmergencyContactFormValues> = useCallback(
    (values) => {
      let nextContacts: EmergencyContactDTO[] = [...contacts];

      // Nếu người dùng tick chọn is_primary = true, lập tức gán is_primary = false cho toàn bộ thẻ khác
      if (values.is_primary) {
        nextContacts = nextContacts.map((c) => ({ ...c, is_primary: false }));
      }

      if (editingId) {
        // Cập nhật liên hệ hiện có
        nextContacts = nextContacts.map((c) =>
          c.id === editingId
            ? { ...c, ...values, id: editingId }
            : c
        );
      } else {
        // Thêm liên hệ mới
        const newContact: EmergencyContactDTO = {
          id: `sos-${crypto.randomUUID()}`,
          ...values,
        };
        // Nếu trong danh sách chưa có primary nào, mặc định thẻ mới làm primary
        if (!nextContacts.some((c) => c.is_primary)) {
          newContact.is_primary = true;
        }
        nextContacts.push(newContact);
      }

      // Đảm bảo luôn có đúng 1 primary nếu danh sách không rỗng
      if (nextContacts.length > 0 && !nextContacts.some((c) => c.is_primary)) {
        nextContacts[0].is_primary = true;
      }

      updateMutation.mutate(nextContacts, {
        onSuccess: () => {
          setIsDialogOpen(false);
          setEditingId(null);
          form.reset();
        },
      });
    },
    [contacts, editingId, updateMutation, form]
  );

  const executeDelete = useCallback(
    (id?: string) => {
      if (!id) return;
      const filtered = contacts.filter((c) => c.id !== id);

      // Nếu sau khi xóa mà không còn thẻ primary nào, gán thẻ đầu tiên làm primary
      if (filtered.length > 0 && !filtered.some((c) => c.is_primary)) {
        filtered[0] = { ...filtered[0], is_primary: true };
      }

      updateMutation.mutate(filtered, {
        onSuccess: () => {
          toast.info("Đã xóa thẻ liên hệ SOS khỏi hệ thống AI Triage.");
          setContactToDelete(null);
        },
      });
    },
    [contacts, updateMutation]
  );

  // Xử lý Xóa liên hệ
  const handleTriggerDelete = useCallback((contact: EmergencyContactDTO) => {
    // Nếu là Người liên hệ số 1 (Primary Target Card), mở AlertDialog xác nhận nghiêm ngặt
    if (contact.is_primary) {
      setContactToDelete(contact);
    } else {
      // Xóa thông thường
      executeDelete(contact.id);
    }
  }, [executeDelete]);

  // Render Loading Skeleton Shimmer
  if (isLoading) {
    return (
      <div className={cn("space-y-6 animate-pulse", className)}>
        <div className="h-12 bg-slate-200 border border-slate-300 rounded-2xl w-1/3 dark:bg-slate-700 dark:border-slate-700" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-56 bg-card border border-border rounded-3xl shadow-sm" />
          <div className="h-56 bg-card border border-border rounded-3xl shadow-sm" />
          <div className="h-56 bg-card border border-border rounded-3xl shadow-sm" />
        </div>
        <div className="h-32 bg-slate-900 rounded-3xl shadow-md" />
      </div>
    );
  }

  // Render Error State
  if (isError) {
    return (
      <div className={cn("bg-rose-50 border border-rose-200 rounded-3xl p-8 text-center max-w-2xl mx-auto space-y-4 shadow-sm", className)}>
        <AlertTriangle className="w-12 h-12 text-rose-600 mx-auto" aria-hidden="true" />
        <h3 className="text-lg font-extrabold text-foreground">Không thể kết nối danh bạ khẩn cấp SOS</h3>
        <p className="text-xs text-slate-600 font-medium dark:text-slate-300">
          Có lỗi xảy ra khi đồng bộ dữ liệu từ máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-6 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-extrabold text-xs transition-all shadow-md shadow-rose-600/25 active:scale-95"
        >
          Thử lại (Retry Query)
        </button>
      </div>
    );
  }

  return (
    <div className={cn("space-y-8", className)}>
      {/* Header Trung Tâm SOS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-border">
        <div className="flex items-center gap-3.5">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50 border border-amber-200 shadow-sm">
            <PhoneCall className="h-6 w-6 text-amber-600 animate-pulse" />
          </div>
          <div>
            <h2 className="text-xl font-black text-foreground tracking-tight flex items-center gap-2.5">
              <span>Trung Tâm Liên Hệ Khẩn Cấp SOS</span>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded-md bg-amber-50 border border-amber-300 text-amber-900 font-extrabold shadow-2xs">
                {contacts.length} / 3
              </span>
            </h2>
            <p className="text-xs text-slate-600 font-medium mt-0.5 dark:text-slate-300">
              Định danh người thân hoặc bác sĩ cá nhân để Điều dưỡng điều xe cấp cứu 115 trong thời gian vàng
            </p>
          </div>
        </div>

        {/* Nút Thêm Liên Hệ Khẩn Cấp */}
        <button
          type="button"
          onClick={handleOpenAdd}
          disabled={isMaxReached || updateMutation.isPending}
          className={cn(
            "h-11 px-5 rounded-2xl font-extrabold text-xs flex items-center justify-center gap-2 transition-all duration-200 shadow-md shrink-0 self-start sm:self-center",
            isMaxReached
              ? "bg-slate-200 text-slate-400 border border-slate-300 cursor-not-allowed dark:bg-slate-700 dark:border-slate-700"
              : "bg-amber-500 hover:bg-amber-400 text-amber-950 shadow-amber-500/25 active:scale-95 font-black"
          )}
        >
          <UserPlus className="w-4 h-4 stroke-[3]" />
          <span>Thêm Người Liên Hệ Khẩn Cấp</span>
        </button>
      </div>

      {/* ===================================================================== */}
      {/* 1. LƯỚI THẺ SOS CỐ ĐỊNH & THẺ ƯU TIÊN 1 (PRIMARY TARGET CARD)       */}
      {/* ===================================================================== */}
      {contacts.length === 0 ? (
        <div className="p-10 rounded-3xl border border-dashed border-slate-300 bg-background text-center space-y-4 max-w-xl mx-auto shadow-sm dark:border-slate-700">
          <div className="w-16 h-16 rounded-2xl bg-amber-100 border border-amber-200 flex items-center justify-center mx-auto shadow-2xs">
            <ShieldAlert className="w-8 h-8 text-amber-600" />
          </div>
          <div className="space-y-1">
            <h4 className="text-base font-black text-foreground">Danh bạ cấp cứu SOS hiện trống</h4>
            <p className="text-xs text-slate-600 leading-relaxed font-normal dark:text-slate-300">
              Khi hệ thống AI Triage phát hiện bệnh nhân chuyển sang trạng thái Báo Động Đỏ (ESI 1 hoặc ESI 2), cần có ít nhất 01 số điện thoại liên hệ lập tức để cứu thâu thời gian vàng.
            </p>
          </div>
          <button
            type="button"
            onClick={handleOpenAdd}
            className="px-6 py-3 rounded-2xl bg-amber-500 hover:bg-amber-400 text-amber-950 font-black text-xs inline-flex items-center gap-2 shadow-lg shadow-amber-500/25 transition-all active:scale-95"
          >
            <UserPlus className="w-4 h-4 stroke-[3]" />
            <span>Khởi Tạo Liên Hệ Đầu Tiên</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <AnimatePresence mode="popLayout">
            {contacts.map((contact) => {
              const isPrimary = contact.is_primary;

              return (
                <motion.div
                  key={contact.id || contact.phone_number}
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9, y: 10 }}
                  transition={{ type: "spring", stiffness: 350, damping: 25 }}
                  className={cn(
                    "p-6 rounded-3xl border transition-all duration-300 relative overflow-hidden flex flex-col justify-between group/sos h-full min-h-[230px]",
                    isPrimary
                      ? "bg-gradient-to-br from-amber-50/95 via-amber-50/40 to-white border-2 border-amber-400 text-foreground shadow-[0_10px_35px_rgba(245,158,11,0.15)] ring-1 ring-amber-500/20 animate-pulse-subtle"
                      : "bg-card border-border/90 hover:border-sky-300 hover:shadow-lg text-foreground shadow-sm"
                  )}
                >
                  {/* Ambient illumination for Primary Card */}
                  {isPrimary && (
                    <div className="absolute -top-12 -right-12 h-36 w-36 rounded-full bg-amber-400/20 blur-2xl pointer-events-none" />
                  )}

                  <div>
                    {/* Top row: Badge & Action buttons */}
                    <div className="flex items-start justify-between gap-2 pb-4 border-b border-border/80">
                      <div>
                        {isPrimary ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500 text-amber-950 font-mono text-[10px] font-black tracking-wider shadow-md shadow-amber-500/35 uppercase">
                            <AlertOctagon className="w-3.5 h-3.5 fill-slate-950 text-amber-500 shrink-0" />
                            <span>NGUỒN LIÊN HỆ CẤP CỨU SỐ 1</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-muted text-slate-700 font-mono text-[10px] font-extrabold tracking-wider uppercase border border-slate-300/80 shadow-2xs dark:text-slate-200 dark:border-slate-700">
                            <Users className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                            <span>LIÊN HỆ BỔ TRỢ</span>
                          </span>
                        )}
                      </div>

                      {/* Edit & Delete Actions */}
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(contact)}
                          className="h-8 w-8 rounded-xl bg-muted hover:bg-slate-200 text-slate-700 hover:text-slate-950 flex items-center justify-center transition-colors border border-slate-300/70 shadow-2xs dark:text-slate-200 dark:hover:bg-slate-700 dark:border-slate-700"
                          title="Chỉnh sửa liên hệ"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleTriggerDelete(contact)}
                          className="h-8 w-8 rounded-xl bg-muted hover:bg-rose-50 text-muted-foreground hover:text-rose-600 flex items-center justify-center transition-colors border border-slate-300/70 hover:border-rose-300 shadow-2xs"
                          title="Xóa liên hệ này"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Contact details */}
                    <div className="mt-4.5 space-y-3">
                      <div className="flex items-baseline justify-between gap-2">
                        <h3 className="text-lg font-black text-foreground tracking-tight flex items-center gap-2 min-w-0">
                          <User className={cn("w-4 h-4 shrink-0", isPrimary ? "text-amber-600" : "text-muted-foreground")} />
                          <span className="truncate">{contact.full_name}</span>
                        </h3>
                        <span className="text-xs font-extrabold px-2.5 py-0.5 rounded-md bg-muted text-slate-800 border border-slate-300/80 shrink-0 font-mono shadow-2xs dark:text-slate-100 dark:border-slate-700">
                          {RELATIONSHIP_OPTIONS.find((r) => r.value === contact.relationship)?.label || contact.relationship}
                        </span>
                      </div>

                      <div className={cn(
                        "flex items-center gap-2.5 p-3.5 rounded-2xl font-mono font-extrabold text-base shadow-inner transition-colors",
                        isPrimary ? "bg-card border border-amber-300/90 text-emerald-800 shadow-xs" : "bg-background border border-border/90 text-emerald-700"
                      )}>
                        <Phone className="w-4 h-4 text-emerald-600 shrink-0" aria-hidden="true" />
                        <span className="tracking-wider">{contact.phone_number}</span>
                      </div>

                      {contact.address && (
                        <div className="flex items-start gap-2 text-xs text-slate-600 font-sans pt-0.5 dark:text-slate-300">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                          <span className="line-clamp-2 leading-relaxed font-medium">{contact.address}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Footer */}
                  <div className="mt-5 pt-3 border-t border-border/80 flex items-center justify-between text-xs font-mono text-muted-foreground">
                    <span className="uppercase font-semibold">Trạng thái: Đã lưu</span>
                    <span className={cn("font-bold flex items-center gap-1", isPrimary ? "text-amber-700 font-extrabold" : "text-emerald-700 font-extrabold")}>
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                      <span>Sẵn sàng ESI 115</span>
                    </span>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 2. HỘP BẢO MẬT LÂM SÀNG PII/PHI NOTICE SHIELD                       */}
      {/* ===================================================================== */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white border border-slate-700 rounded-3xl p-6 md:p-8 shadow-xl relative overflow-hidden group transition-all duration-500">
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-amber-400/10 to-transparent pointer-events-none" />
        <div className="absolute -left-20 -bottom-20 h-48 w-48 rounded-full bg-sky-500/10 blur-[80px] pointer-events-none" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 relative z-10">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-amber-500/20 border border-amber-400/50 shadow-[0_0_30px_rgba(245,158,11,0.3)] group-hover:scale-105 transition-transform duration-300">
            <ShieldCheck className="h-9 w-9 text-amber-400 animate-pulse" />
          </div>

          <div className="space-y-2.5 flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Nội dung phải khớp đúng những gì hệ thống làm: số điện thoại
                  được lưu và trả về dạng văn bản thường cho nhân viên y tế xem
                  ca (routes_nurse_simple.py), không có tầng mã hoá nào, và
                  không có cơ chế tự gọi hay điều xe 115. */}
              <span className="text-xs font-mono font-black px-3 py-1 rounded-md bg-amber-500 text-amber-950 uppercase tracking-wider shadow-sm">
                Ai được xem số này
              </span>
            </div>
            <p className="text-sm md:text-base text-slate-200 font-normal leading-relaxed">
              <strong className="text-amber-300 font-extrabold">Chỉ nhân viên y tế đang xem ca sàng lọc của bạn.</strong> Số điện thoại người thân được lưu trong hồ sơ của bạn và hiển thị cho nhân viên y tế khi họ thẩm định ca, để liên lạc khi cần. Hệ thống không tự gọi số này và không tự điều xe 115.
            </p>
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* 3. MODAL FORM SÁT KÉP (DIALOG THÊM/SỬA LIÊN HỆ)                        */}
      {/* ===================================================================== */}
      <AnimatePresence>
        {isDialogOpen && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="sos-modal-title"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: "spring", stiffness: 350, damping: 25 }}
              className="bg-card border border-border rounded-3xl shadow-[0_25px_70px_rgba(0,0,0,0.2)] w-full max-w-lg p-6 md:p-8 relative overflow-hidden text-foreground"
            >
              <div className="absolute top-0 right-0 w-48 h-48 bg-amber-50 rounded-full blur-3xl pointer-events-none -z-10" />

              <div className="flex items-center justify-between pb-4 border-b border-border">
                <div className="flex items-center gap-3">
                  <div className="h-11 w-11 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shadow-sm">
                    {editingId ? <Edit3 className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
                  </div>
                  <h3 id="sos-modal-title" className="text-lg font-black text-foreground">
                    {editingId ? "Cập Nhật Liên Hệ Khẩn Cấp" : "Thêm Người Liên Hệ Khẩn Cấp"}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setIsDialogOpen(false)}
                  className="h-8 w-8 rounded-xl bg-muted hover:bg-slate-200 text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors shadow-2xs dark:hover:bg-slate-700"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Form Nội Dung */}
              <form onSubmit={form.handleSubmit(onSubmit)} className="mt-6 space-y-5">
                {/* Họ và tên */}
                <div className="space-y-2">
                  <label htmlFor="input-sos-name" className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5 dark:text-slate-100">
                    <User className="w-3.5 h-3.5 text-amber-600" />
                    <span>Họ và tên người liên hệ:</span>
                  </label>
                  <input
                    id="input-sos-name"
                    type="text"
                    placeholder="Vd: Nguyễn Văn Hùng (Cha)"
                    className={cn(
                      "w-full h-11 px-4 bg-background border rounded-xl text-sm text-foreground font-bold focus:outline-none focus:bg-card focus:ring-2 focus:ring-amber-500/40 transition-all shadow-inner",
                      form.formState.errors.full_name ? "border-rose-500 bg-rose-50/50 text-rose-900" : "border-slate-300 focus:border-amber-500 dark:border-slate-700"
                    )}
                    {...form.register("full_name")}
                  />
                  {form.formState.errors.full_name && (
                    <p className="text-xs font-bold text-rose-600 flex items-center gap-1 mt-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                      <span>{form.formState.errors.full_name.message}</span>
                    </p>
                  )}
                </div>

                {/* Mối quan hệ */}
                <div className="space-y-2">
                  <label className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5 dark:text-slate-100">
                    <Users className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Mối quan hệ (Relationship):</span>
                  </label>
                  <Controller
                    control={form.control}
                    name="relationship"
                    render={({ field }) => (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {RELATIONSHIP_OPTIONS.map((opt) => (
                          <button
                            key={opt.value}
                            type="button"
                            onClick={() => field.onChange(opt.value)}
                            className={cn(
                              "h-9 px-2 rounded-xl border text-xs transition-all flex items-center justify-center shadow-2xs",
                              field.value === opt.value
                                ? "bg-amber-500 text-amber-950 border-amber-500 font-black shadow-md shadow-amber-500/25"
                                : "bg-muted text-slate-700 border-slate-300 hover:bg-slate-200/60 font-bold dark:text-slate-200 dark:hover:bg-slate-700 dark:border-slate-700"
                            )}
                          >
                            <span>{opt.label}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  />
                </div>

                {/* Số điện thoại (Zod validation) */}
                <div className="space-y-2">
                  <label htmlFor="input-sos-phone" className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5 dark:text-slate-100">
                    <Phone className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Số điện thoại di động:</span>
                  </label>
                  <input
                    id="input-sos-phone"
                    type="tel"
                    placeholder="Vd: 0901234567 hoặc +84901234567"
                    className={cn(
                      "w-full h-11 px-4 bg-background border rounded-xl text-sm font-mono font-black text-foreground focus:outline-none focus:bg-card focus:ring-2 focus:ring-emerald-500/40 transition-all placeholder:text-slate-400 shadow-inner",
                      form.formState.errors.phone_number ? "border-rose-500 bg-rose-50/50 text-rose-900" : "border-slate-300 focus:border-emerald-500 dark:border-slate-700"
                    )}
                    {...form.register("phone_number")}
                  />
                  {form.formState.errors.phone_number && (
                    <p className="text-xs font-bold text-rose-600 flex items-center gap-1 mt-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                      <span>{form.formState.errors.phone_number.message}</span>
                    </p>
                  )}
                </div>

                {/* Địa chỉ (tuỳ chọn) */}
                <div className="space-y-2">
                  <label htmlFor="input-sos-address" className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5 dark:text-slate-100">
                    <MapPin className="w-3.5 h-3.5 text-sky-600" />
                    <span>Địa chỉ / Căn hộ (Hỗ trợ xe cấp cứu 115):</span>
                  </label>
                  <input
                    id="input-sos-address"
                    type="text"
                    placeholder="Vd: Vinhomes Central Park, Q. Bình Thạnh, TP.HCM"
                    className="w-full h-11 px-4 bg-background border border-slate-300 rounded-xl text-sm font-semibold text-foreground focus:outline-none focus:bg-card focus:ring-2 focus:ring-sky-500/40 focus:border-sky-500 transition-all placeholder:text-slate-400 shadow-inner dark:border-slate-700"
                    {...form.register("address")}
                  />
                </div>

                {/* Cờ ưu tiên số 1 (Is Primary) */}
                <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-300/80 flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-3">
                    <AlertOctagon className="w-6 h-6 text-amber-600 shrink-0 animate-pulse" />
                    <div className="text-xs">
                      <div className="font-extrabold text-amber-950">Đặt làm Nguồn liên hệ cấp cứu số 1</div>
                      <div className="text-slate-600 text-xs font-medium mt-0.5 dark:text-slate-300">Số này được hiển thị đầu tiên cho nhân viên y tế khi cần liên lạc</div>
                    </div>
                  </div>
                  <Controller
                    control={form.control}
                    name="is_primary"
                    render={({ field }) => (
                      <button
                        type="button"
                        onClick={() => field.onChange(!field.value)}
                        className={cn(
                          "w-12 h-7 rounded-full transition-colors relative p-1 shrink-0 flex items-center shadow-inner",
                          field.value ? "bg-amber-500" : "bg-slate-300"
                        )}
                      >
                        <span
                          className={cn(
                            "w-5 h-5 rounded-full bg-card shadow-md transform transition-transform duration-200",
                            field.value ? "translate-x-5 bg-slate-950" : "translate-x-0"
                          )}
                        />
                      </button>
                    )}
                  />
                </div>

                {/* Submit actions */}
                <div className="pt-5 flex items-center justify-end gap-3 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setIsDialogOpen(false)}
                    className="h-10 px-5 rounded-xl bg-muted hover:bg-slate-200 text-slate-700 font-bold text-xs transition-colors shadow-2xs dark:text-slate-200 dark:hover:bg-slate-700"
                  >
                    Hủy Bỏ
                  </button>
                  <button
                    type="submit"
                    disabled={updateMutation.isPending}
                    className="h-10 px-6 rounded-xl bg-amber-500 hover:bg-amber-400 text-amber-950 font-black text-xs flex items-center gap-2 shadow-lg shadow-amber-500/25 transition-all active:scale-95 disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4 stroke-[3]" />
                    <span>{editingId ? "Lưu Cập Nhật" : "Xác Nhận Thêm"}</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ===================================================================== */}
      {/* 4. ALERT DIALOG XÁC NHẬN XÓA NGUỒN LIÊN HỆ CẤP CỨU SỐ 1              */}
      {/* ===================================================================== */}
      <AnimatePresence>
        {contactToDelete && (
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="alert-dialog-title"
            aria-describedby="alert-dialog-desc"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/65 backdrop-blur-md"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-card border-2 border-rose-500 rounded-3xl p-6 md:p-8 max-w-md w-full text-foreground shadow-[0_20px_60px_rgba(244,63,94,0.25)] relative overflow-hidden"
            >
              <div className="flex items-center gap-3 text-rose-600 mb-4">
                <div className="h-12 w-12 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center shrink-0 shadow-sm">
                  <AlertTriangle className="w-6 h-6 text-rose-600" aria-hidden="true" />
                </div>
                <h3 id="alert-dialog-title" className="text-lg font-black text-foreground leading-tight">
                  CẢNH BÁO: Xóa Nguồn Liên Hệ Số 1 (Primary Target)?
                </h3>
              </div>

              <p id="alert-dialog-desc" className="text-xs md:text-sm text-slate-600 leading-relaxed font-normal mb-6 dark:text-slate-300">
                Bạn đang xóa liên hệ <strong className="text-amber-900 font-extrabold bg-amber-50 px-1 py-0.5 rounded">{contactToDelete.full_name}</strong>. Đây là số điện thoại ưu tiên mà điều dưỡng lâm sàng sẽ liên lạc đầu tiên khi ca khám chuyển sang <strong className="text-rose-700 font-bold bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">Báo Động Đỏ (ESI 1 hoặc ESI 2)</strong>. Bạn có chắc chắn muốn ngừng ghi nhận số này?
              </p>
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setContactToDelete(null)}
                  className="px-5 py-2.5 rounded-xl bg-muted hover:bg-slate-200 text-slate-700 font-bold text-xs transition-all shadow-2xs dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  Hủy Bỏ An Toàn
                </button>
                <button
                  type="button"
                  onClick={() => executeDelete(contactToDelete.id)}
                  disabled={updateMutation.isPending}
                  className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-black text-xs transition-all shadow-lg shadow-rose-600/25 flex items-center gap-1.5 active:scale-95"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Xác Nhận Xóa Ngay</span>
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
