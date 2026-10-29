"use client";

import React, { useCallback, useMemo, useState } from "react";
import { Controller, useForm, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { Check, Loader2, MapPin, Pencil, Phone, Plus, Trash2, TriangleAlert, X } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { avatarInitial } from "@/components/patient/family-identity";
import { enterTransition, exitTransition, layoutTransition } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { formatVietnamPhoneForDisplay } from "@/lib/validations/account-contact.schema";
import { useEmergencyContacts } from "@/queries/use-clinical-profile";
import { useUpdateEmergencyContacts } from "@/queries/use-profile-mutations";
import { EmergencyContactSchema, type EmergencyContactFormValues } from "@/schemas/clinical-profile.schema";
import type { EmergencyContactDTO, RelationshipType } from "@/types/clinical-profile";

// ============================================================================
// 1. CONSTANTS
// ============================================================================
const MAX_CONTACTS = 3;

const RELATIONSHIP_OPTIONS: Array<{ value: RelationshipType; label: string }> = [
  { value: "SPOUSE", label: "Vợ / Chồng" },
  { value: "PARENT", label: "Cha / Mẹ" },
  { value: "CHILD", label: "Con cái" },
  { value: "SIBLING", label: "Anh / Chị / Em" },
  { value: "FRIEND", label: "Bạn bè / Đồng nghiệp" },
  { value: "OTHER", label: "Người thân khác" },
];

function relationshipLabel(value: RelationshipType): string {
  return RELATIONSHIP_OPTIONS.find((option) => option.value === value)?.label ?? "Người thân khác";
}

/** `tel:` chỉ nhận chữ số và dấu +, bỏ khoảng trắng hay gạch người dùng gõ vào. */
function telHref(phoneNumber: string): string {
  return `tel:${phoneNumber.replace(/[^\d+]/g, "")}`;
}

/** Người liên hệ mới nổi lên, người bị xóa mờ đi, những người còn lại dời chỗ. */
const contactVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: enterTransition },
  exit: { opacity: 0, transition: exitTransition },
};

const FIELD_INPUT =
  "min-h-12 w-full rounded-xl border bg-background px-4 text-base text-foreground outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-card";

export interface EmergencySosManagerProps {
  className?: string;
  /** Tên người đang được chọn, để câu mô tả nói rõ đây là liên hệ của ai. */
  subjectName?: string;
}

/**
 * Người liên hệ khẩn cấp của hồ sơ đang chọn (tối đa 3). Người số 1 là người
 * nhân viên y tế thấy khi thẩm định ca sàng lọc của hồ sơ này
 * (`routes_nurse_simple.py` chỉ trả về liên hệ số 1); hệ thống không tự gọi số
 * nào và không tự điều xe 115. Mọi câu chữ ở đây phải khớp đúng điều đó.
 */
export const EmergencySosManager: React.FC<EmergencySosManagerProps> = ({ className, subjectName }) => {
  const { data: contactsData, isLoading, isError, refetch } = useEmergencyContacts();
  const updateMutation = useUpdateEmergencyContacts();

  const contacts = useMemo(() => contactsData ?? [], [contactsData]);
  const isMaxReached = contacts.length >= MAX_CONTACTS;

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  // Xóa người liên hệ số 1 luôn phải xác nhận lại; người khác xóa ngay.
  const [contactToDelete, setContactToDelete] = useState<EmergencyContactDTO | null>(null);

  const form = useForm<EmergencyContactFormValues>({
    resolver: zodResolver(EmergencyContactSchema),
    defaultValues: {
      full_name: "",
      relationship: "SPOUSE",
      phone_number: "",
      is_primary: contacts.length === 0,
      address: "",
    },
  });
  const { errors } = form.formState;

  const closeDialog = useCallback(() => {
    setIsDialogOpen(false);
    setEditingId(null);
  }, []);

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
      is_primary: contacts.length === 0 || !contacts.some((contact) => contact.is_primary),
      address: "",
    });
    setIsDialogOpen(true);
  }, [isMaxReached, contacts, form]);

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
    [form],
  );

  const onSubmit: SubmitHandler<EmergencyContactFormValues> = useCallback(
    (values) => {
      let nextContacts: EmergencyContactDTO[] = [...contacts];

      // Chỉ có đúng một người số 1: chọn người này thì bỏ cờ của mọi người khác.
      if (values.is_primary) {
        nextContacts = nextContacts.map((contact) => ({ ...contact, is_primary: false }));
      }

      if (editingId) {
        nextContacts = nextContacts.map((contact) =>
          contact.id === editingId ? { ...contact, ...values, id: editingId } : contact,
        );
      } else {
        const newContact: EmergencyContactDTO = { id: `sos-${crypto.randomUUID()}`, ...values };
        if (!nextContacts.some((contact) => contact.is_primary)) newContact.is_primary = true;
        nextContacts.push(newContact);
      }

      // Danh sách không rỗng thì luôn có đúng một người số 1.
      if (nextContacts.length > 0 && !nextContacts.some((contact) => contact.is_primary)) {
        nextContacts[0].is_primary = true;
      }

      updateMutation.mutate(nextContacts, {
        onSuccess: () => {
          closeDialog();
          form.reset();
        },
      });
    },
    [contacts, editingId, updateMutation, form, closeDialog],
  );

  const executeDelete = useCallback(
    (id?: string) => {
      if (!id) return;
      const filtered = contacts.filter((contact) => contact.id !== id);
      // Xóa người số 1 thì người kế tiếp lên làm số 1.
      if (filtered.length > 0 && !filtered.some((contact) => contact.is_primary)) {
        filtered[0] = { ...filtered[0], is_primary: true };
      }
      updateMutation.mutate(filtered, {
        onSuccess: () => setContactToDelete(null),
      });
    },
    [contacts, updateMutation],
  );

  const handleTriggerDelete = useCallback(
    (contact: EmergencyContactDTO) => {
      if (contact.is_primary) setContactToDelete(contact);
      else executeDelete(contact.id);
    },
    [executeDelete],
  );

  const sectionDescription = (
    <>
      Khi thẩm định ca sàng lọc của {subjectName ?? "hồ sơ này"}, nhân viên y tế thấy người liên hệ số 1 để gọi khi
      cần. Hệ thống không tự gọi số này và không tự điều xe 115.
    </>
  );

  return (
    <section
      aria-labelledby="sos-contacts-title"
      className={cn("rounded-3xl border border-border bg-card p-4 shadow-xs sm:p-6", className)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 id="sos-contacts-title" className="text-lg font-extrabold tracking-tight text-foreground">
            Người liên hệ khẩn cấp
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{sectionDescription}</p>
        </div>
        {!isLoading && !isError && (
          <span className="shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
            {contacts.length}/{MAX_CONTACTS}
          </span>
        )}
      </div>

      {isLoading ? (
        <div aria-busy="true" aria-label="Đang tải người liên hệ khẩn cấp" className="mt-4 space-y-2">
          {[0, 1].map((item) => (
            <div key={item} className="skeleton-sweep relative flex items-center gap-4 overflow-hidden rounded-2xl p-2">
              <div className="size-12 shrink-0 rounded-full bg-muted" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-1/2 rounded-lg bg-muted" />
                <div className="h-4 w-1/3 rounded-lg bg-muted" />
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <div
          role="alert"
          className="mt-4 space-y-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100"
        >
          <p className="text-sm font-semibold leading-6">
            Không tải được danh sách người liên hệ khẩn cấp. Vui lòng kiểm tra kết nối mạng và thử lại.
          </p>
          <button
            type="button"
            onClick={() => void refetch()}
            className="flex min-h-11 items-center gap-2 rounded-xl border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 dark:border-rose-800 dark:text-rose-200 dark:hover:bg-rose-950"
          >
            Thử lại
          </button>
        </div>
      ) : contacts.length === 0 ? (
        <div className="mt-4 space-y-4 rounded-2xl border border-dashed border-border p-4 text-center">
          <p className="text-sm leading-6 text-muted-foreground">
            Chưa có người liên hệ khẩn cấp. Thêm ít nhất một người để nhân viên y tế có số gọi khi cần.
          </p>
          <button
            type="button"
            onClick={handleOpenAdd}
            className="mx-auto flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-brand-foreground transition duration-[180ms] hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
          >
            <Plus className="size-4" aria-hidden="true" />
            Thêm người liên hệ
          </button>
        </div>
      ) : (
        <>
          <ul className="mt-4 divide-y divide-border">
            <AnimatePresence initial={false}>
              {contacts.map((contact) => (
                <motion.li
                  key={contact.id || contact.phone_number}
                  layout="position"
                  variants={contactVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  transition={{ layout: layoutTransition }}
                  className="py-4 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-4">
                    <span
                      aria-hidden="true"
                      className="flex size-12 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-base font-extrabold text-indigo-900 dark:bg-indigo-950 dark:text-indigo-200"
                    >
                      {avatarInitial(contact.full_name)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-base font-bold leading-6 text-foreground">
                        {contact.full_name}
                        <span className="font-semibold text-muted-foreground">
                          {" "}
                          · {relationshipLabel(contact.relationship).toLocaleLowerCase("vi-VN")}
                        </span>
                      </p>
                      <p className="text-sm leading-6 tabular-nums text-muted-foreground">
                        {formatVietnamPhoneForDisplay(contact.phone_number)}
                      </p>
                      {contact.is_primary && (
                        <span className="mt-2 inline-flex items-center gap-2 rounded-full border border-brand-edge bg-brand-soft px-2 text-sm font-semibold leading-6 text-brand-ink">
                          Liên hệ số 1
                        </span>
                      )}
                      {contact.address && (
                        <p className="mt-2 flex items-start gap-2 text-sm leading-6 text-muted-foreground">
                          <MapPin className="mt-1 size-4 shrink-0" aria-hidden="true" />
                          <span className="line-clamp-2">{contact.address}</span>
                        </p>
                      )}
                    </div>
                    <a
                      href={telHref(contact.phone_number)}
                      aria-label={`Gọi ${contact.full_name}`}
                      className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-brand-edge bg-brand-soft text-brand transition duration-[180ms] hover:bg-brand hover:text-brand-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
                    >
                      <Phone className="size-5" aria-hidden="true" />
                    </a>
                  </div>
                  <div className="mt-2 flex gap-2 pl-16">
                    <button
                      type="button"
                      onClick={() => handleOpenEdit(contact)}
                      aria-label={`Sửa người liên hệ ${contact.full_name}`}
                      className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
                    >
                      <Pencil className="size-4" aria-hidden="true" />
                      Sửa
                    </button>
                    <button
                      type="button"
                      onClick={() => handleTriggerDelete(contact)}
                      disabled={updateMutation.isPending}
                      aria-label={`Xóa người liên hệ ${contact.full_name}`}
                      className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 disabled:opacity-50 dark:text-rose-300 dark:hover:bg-rose-950/40"
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                      Xóa
                    </button>
                  </div>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>

          <div className="mt-4 border-t border-border pt-4">
            {isMaxReached ? (
              <p className="text-sm leading-6 text-muted-foreground">
                Đã đủ {MAX_CONTACTS} người liên hệ. Xóa bớt một người nếu muốn thêm người khác.
              </p>
            ) : (
              <button
                type="button"
                onClick={handleOpenAdd}
                disabled={updateMutation.isPending}
                className="flex min-h-11 items-center gap-2 rounded-xl border border-dashed border-border px-4 text-sm font-semibold text-brand transition-colors hover:border-brand-edge hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-50"
              >
                <Plus className="size-4" aria-hidden="true" />
                Thêm người liên hệ
              </button>
            )}
          </div>
        </>
      )}

      {/* ===================================================================== */}
      {/* HỘP THOẠI THÊM / SỬA (React Hook Form + Zod, cùng schema như trước)   */}
      {/* ===================================================================== */}
      <Dialog
        open={isDialogOpen}
        onOpenChange={(open) => {
          if (!open) closeDialog();
        }}
      >
        <DialogContent
          hideCloseButton
          overlayClassName="bg-slate-950/55 backdrop-blur-sm"
          className="max-h-[calc(100dvh-32px)] max-w-lg gap-0 overflow-y-auto rounded-3xl border-border bg-card p-0 text-foreground shadow-xl"
        >
          <DialogHeader className="space-y-2 border-b border-border p-6 pr-16 text-left">
            <DialogTitle className="text-xl font-bold text-foreground">
              {editingId ? "Sửa người liên hệ khẩn cấp" : "Thêm người liên hệ khẩn cấp"}
            </DialogTitle>
            <DialogDescription className="text-sm leading-6 text-muted-foreground">
              Người liên hệ số 1 được hiển thị cho nhân viên y tế khi họ thẩm định ca sàng lọc.
            </DialogDescription>
          </DialogHeader>
          <DialogClose asChild>
            <button
              type="button"
              aria-label="Đóng hộp thoại"
              className="absolute right-4 top-4 flex size-11 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              <X className="size-5" aria-hidden="true" />
            </button>
          </DialogClose>

          <form id="sos-contact-form" noValidate onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 p-6">
            <div className="space-y-2">
              <label htmlFor="input-sos-name" className="block text-sm font-semibold text-foreground">
                Họ và tên người liên hệ
              </label>
              <input
                id="input-sos-name"
                type="text"
                autoComplete="name"
                placeholder="Ví dụ: Nguyễn Văn Hùng"
                aria-invalid={Boolean(errors.full_name)}
                aria-describedby={errors.full_name ? "input-sos-name-error" : undefined}
                className={cn(
                  FIELD_INPUT,
                  errors.full_name
                    ? "border-rose-500 focus-visible:ring-rose-600"
                    : "border-border focus-visible:border-brand focus-visible:ring-brand",
                )}
                {...form.register("full_name")}
              />
              {errors.full_name?.message && (
                <p id="input-sos-name-error" className="flex items-center gap-2 text-sm font-medium text-rose-700 dark:text-rose-300">
                  <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
                  {errors.full_name.message}
                </p>
              )}
            </div>

            <fieldset className="space-y-2">
              <legend className="text-sm font-semibold text-foreground">Mối quan hệ</legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {RELATIONSHIP_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className="relative flex min-h-11 cursor-pointer items-center justify-center rounded-xl border border-border bg-background px-2 text-center text-sm font-semibold text-foreground transition-colors focus-within:ring-2 focus-within:ring-brand focus-within:ring-offset-2 focus-within:ring-offset-card hover:bg-muted has-[:checked]:border-brand-edge has-[:checked]:bg-brand-soft has-[:checked]:text-brand-ink"
                  >
                    <input type="radio" value={option.value} className="sr-only" {...form.register("relationship")} />
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="space-y-2">
              <label htmlFor="input-sos-phone" className="block text-sm font-semibold text-foreground">
                Số điện thoại
              </label>
              <input
                id="input-sos-phone"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="Ví dụ: 0901234567 hoặc +84901234567"
                aria-invalid={Boolean(errors.phone_number)}
                aria-describedby={errors.phone_number ? "input-sos-phone-error" : undefined}
                className={cn(
                  FIELD_INPUT,
                  "tabular-nums",
                  errors.phone_number
                    ? "border-rose-500 focus-visible:ring-rose-600"
                    : "border-border focus-visible:border-brand focus-visible:ring-brand",
                )}
                {...form.register("phone_number")}
              />
              {errors.phone_number?.message && (
                <p id="input-sos-phone-error" className="flex items-center gap-2 text-sm font-medium text-rose-700 dark:text-rose-300">
                  <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
                  {errors.phone_number.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label htmlFor="input-sos-address" className="block text-sm font-semibold text-foreground">
                Địa chỉ <span className="font-normal text-muted-foreground">(không bắt buộc)</span>
              </label>
              <input
                id="input-sos-address"
                type="text"
                autoComplete="street-address"
                placeholder="Ví dụ: 12 Nguyễn Trãi, Thanh Xuân, Hà Nội"
                className={cn(FIELD_INPUT, "border-border focus-visible:border-brand focus-visible:ring-brand")}
                {...form.register("address")}
              />
            </div>

            <Controller
              control={form.control}
              name="is_primary"
              render={({ field }) => (
                <div className="flex items-center justify-between gap-4 rounded-2xl border border-border bg-muted/60 p-4">
                  <div className="min-w-0">
                    <p id="sos-primary-label" className="text-sm font-bold text-foreground">
                      Đặt làm người liên hệ số 1
                    </p>
                    <p id="sos-primary-hint" className="text-sm leading-6 text-muted-foreground">
                      Nhân viên y tế thấy người này đầu tiên khi cần liên lạc.
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={field.value}
                    aria-labelledby="sos-primary-label"
                    aria-describedby="sos-primary-hint"
                    onClick={() => field.onChange(!field.value)}
                    className={cn(
                      "relative flex h-8 w-14 shrink-0 items-center rounded-full p-1 transition-colors duration-[180ms] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card",
                      field.value ? "bg-brand" : "bg-slate-300 dark:bg-slate-600",
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn(
                        "size-6 rounded-full bg-white shadow-sm transition-transform duration-[180ms] motion-reduce:transition-none",
                        field.value ? "translate-x-6" : "translate-x-0",
                      )}
                    />
                  </button>
                </div>
              )}
            />
          </form>

          <footer className="flex flex-col-reverse gap-2 border-t border-border p-4 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={closeDialog}
              className="flex min-h-12 items-center justify-center rounded-xl border border-border bg-card px-6 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              Hủy
            </button>
            <button
              type="submit"
              form="sos-contact-form"
              disabled={updateMutation.isPending}
              className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-brand px-6 text-base font-bold text-brand-foreground transition duration-[180ms] hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card active:scale-[0.97] disabled:opacity-60 motion-reduce:transition-none motion-reduce:active:scale-100"
            >
              {updateMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Check className="size-4" aria-hidden="true" />
              )}
              {editingId ? "Lưu thay đổi" : "Thêm người liên hệ"}
            </button>
          </footer>
        </DialogContent>
      </Dialog>

      {/* ===================================================================== */}
      {/* XÁC NHẬN XÓA NGƯỜI LIÊN HỆ SỐ 1                                        */}
      {/* ===================================================================== */}
      <Dialog
        open={contactToDelete !== null}
        onOpenChange={(open) => {
          if (!open && !updateMutation.isPending) setContactToDelete(null);
        }}
      >
        <DialogContent
          role="alertdialog"
          hideCloseButton
          overlayClassName="bg-slate-950/55 backdrop-blur-sm"
          className="max-w-md gap-0 rounded-3xl border-border bg-card p-0 text-foreground shadow-xl"
        >
          <DialogHeader className="space-y-4 border-b border-border p-6 text-left">
            <div className="flex items-center gap-4">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300">
                <TriangleAlert className="size-5" aria-hidden="true" />
              </span>
              <DialogTitle className="text-lg font-bold text-foreground">Xóa người liên hệ số 1?</DialogTitle>
            </div>
            <DialogDescription className="text-sm leading-6 text-muted-foreground">
              Bạn đang xóa <strong className="text-foreground">{contactToDelete?.full_name}</strong>, người nhân viên y tế
              thấy đầu tiên khi cần liên lạc trong lúc thẩm định ca.
              {contacts.length > 1
                ? " Người liên hệ kế tiếp trong danh sách sẽ thành số 1."
                : " Sau khi xóa, hồ sơ này sẽ không còn người liên hệ khẩn cấp nào."}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col-reverse gap-2 p-4 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={() => setContactToDelete(null)}
              disabled={updateMutation.isPending}
              className="flex min-h-11 items-center justify-center rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-50"
            >
              Giữ lại
            </button>
            <button
              type="button"
              onClick={() => executeDelete(contactToDelete?.id)}
              disabled={updateMutation.isPending}
              className="flex min-h-11 items-center justify-center gap-2 rounded-xl bg-rose-600 px-4 text-sm font-bold text-white transition-colors hover:bg-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              {updateMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Trash2 className="size-4" aria-hidden="true" />
              )}
              Xóa người này
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
};
