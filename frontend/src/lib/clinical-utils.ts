import type { EhrLiteDTO, BmiResultDTO } from "@/types/clinical-profile";

/**
 * ============================================================================
 * CLINICAL UTILITY & BUSINESS LOGIC FUNCTIONS (ZERO `any` TOLERANCE)
 * ============================================================================
 * Bộ hàm xử lý logic lâm sàng tinh khiết (Pure Business Logic):
 * 1. Tính toán BMI theo quy chuẩn Châu Á / WHO (IDA & WHO WPRO)
 * 2. Tạo bản xem trước ngữ cảnh lâm sàng có cấu trúc cho DeepAgent
 */

/**
 * Tính toán Chỉ số Khối Cơ Thể (BMI) theo chuẩn Lâm sàng cho người Châu Á / WHO.
 * 
 * @param heightCm - Chiều cao tính bằng cm (50 - 250)
 * @param weightKg - Cân nặng tính bằng kg (3 - 350)
 * @returns BmiResultDTO với bmi đã làm tròn 1 chữ số thập phân, phân loại, màu tailwind và khuyến nghị y khoa
 */
export const calculateBMI = (heightCm: number | null | undefined, weightKg: number | null | undefined): BmiResultDTO => {
  if (heightCm == null || weightKg == null || heightCm <= 0 || weightKg <= 0 || Number.isNaN(heightCm) || Number.isNaN(weightKg)) {
    return {
      bmi: 0,
      category: "NORMAL",
      colorClass: "text-slate-500 bg-slate-500/10 border-slate-500/20",
      advice: "Thông số chiều cao và cân nặng chưa hợp lệ để tính chỉ số BMI.",
    };
  }

  const heightM = heightCm / 100;
  const rawBmi = weightKg / (heightM * heightM);
  const bmi = Math.round(rawBmi * 10) / 10;

  // Tiêu chuẩn BMI cho người Châu Á (IDA / WHO WPRO standard)
  if (bmi < 18.5) {
    return {
      bmi,
      category: "UNDERWEIGHT",
      colorClass: "text-sky-600 dark:text-sky-400 bg-sky-500/10 border-sky-500/20",
      advice: "Cân nặng thấp hơn tiêu chuẩn (Thiếu cân). Cần tăng cường dinh dưỡng, bổ sung đạm, protein và năng lượng một cách cân đối.",
    };
  } else if (bmi < 23.0) {
    return {
      bmi,
      category: "NORMAL",
      colorClass: "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      advice: "Chỉ số BMI lý tưởng theo tiêu chuẩn lâm sàng Châu Á. Tiếp tục duy trì chế độ dinh dưỡng lành mạnh và vận động đều đặn.",
    };
  } else if (bmi < 25.0) {
    return {
      bmi,
      category: "OVERWEIGHT",
      colorClass: "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20",
      advice: "Cân nặng ở ngưỡng Tiền béo phì / Thừa cân (chuẩn Châu Á). Cần kiểm soát tổng chi phí năng lượng, hạn chế carbohydrate tinh chế và mỡ động vật.",
    };
  } else {
    return {
      bmi,
      category: "OBESE",
      colorClass: "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20",
      advice: "Chỉ số BMI ở ngưỡng Béo phì (Độ I/II chuẩn Châu Á). Cần có kế hoạch giảm cân chuyên sâu, đánh giá định kỳ huyết áp, đường huyết và chỉ số tim mạch.",
    };
  }
};

/**
 * Tạo bản xem trước ngữ cảnh lâm sàng có cấu trúc từ hồ sơ bệnh nhân.
 * Dữ liệu này vẫn phải được bệnh nhân xác nhận trong phiên triage hiện tại.
 *
 * @param ehr - Hồ sơ lâm sàng rút gọn (EhrLiteDTO)
 * @returns Chuỗi SBAR chỉ dùng để xem trước verified clinical context
 */
export const generateVerifiedClinicalContext = (ehr: EhrLiteDTO): string => {
  const bmiResult = calculateBMI(ehr.height_cm, ehr.weight_kg);
  
  const formattedConditions =
    ehr.chronic_conditions && ehr.chronic_conditions.length > 0
      ? ehr.chronic_conditions.join("; ")
      : "None recorded (Không ghi nhận bệnh nền)";

  const formattedAllergies =
    ehr.allergies && ehr.allergies.length > 0
      ? ehr.allergies
          .map((a) => `${a.name} [Type: ${a.type} | Severity: ${a.severity}]`)
          .join("; ")
      : "None recorded (Không ghi nhận dị ứng y khoa)";

  const formattedMedications =
    ehr.current_medications && ehr.current_medications.length > 0
      ? ehr.current_medications
          .map((m) => `${m.name} (Dosage: ${m.dosage}, Freq: ${m.frequency})`)
          .join("; ")
      : "None currently taking (Không dùng thuốc điều trị thường xuyên)";

  const hasHighAllergy = ehr.allergies?.some((a) => a.severity === "HIGH");
  const hasCardiovascularRisk = ehr.chronic_conditions?.some((c) =>
    /stent|cardio|hypertension|heart|mạch|tim|huyết áp|coronary/i.test(c)
  );

  const riskAlerts: string[] = [];
  if (hasHighAllergy) {
    riskAlerts.push(
      "[ALERT 1] HIGH SEVERITY ALLERGY RECORDED: Confirm this history during the active session and send it for clinical review."
    );
  }
  if (hasCardiovascularRisk) {
    riskAlerts.push(
      "[ALERT 2] CARDIOVASCULAR / CORONARY HISTORY RECORDED: Treat this as unconfirmed context until the patient reviews it in the active session."
    );
  }
  if (riskAlerts.length === 0) {
    riskAlerts.push("No static profile alert is recorded; current symptoms still require independent safety screening.");
  }

  return `=== [MEDTRIAGE VERIFIED CLINICAL CONTEXT PREVIEW] ===
[PATIENT BIOMETRICS & DEMOGRAPHIC PROFILE]
• Age: ${ehr.age} | Gender: ${ehr.gender} | Blood Type: ${ehr.blood_type}
• Biometrics: Height ${ehr.height_cm}cm, Weight ${ehr.weight_kg}kg | BMI: ${bmiResult.bmi} (${bmiResult.category} according to WHO Asian Standards)
• Last Clinical Update: ${ehr.last_updated || "N/A"}

================ SBAR CLINICAL CONTEXT PROTOCOL ================
[S] - SITUATION:
Patient profile context prepared for review during an interactive triage session.

[B] - BACKGROUND (EHR LITE SUMMARY):
• Chronic Conditions: ${formattedConditions}
• Clinical Allergies: ${formattedAllergies}
• Active Medications: ${formattedMedications}

[A] - ASSESSMENT (AUTOMATED CLINICAL RISK SHIELD):
${riskAlerts.map((alert) => `• ${alert}`).join("\n")}

[R] - VERIFIED CONTEXT REQUIREMENTS:
1. Require patient confirmation before using historical profile facts in the active triage turn.
2. Do not convert missing or stale profile values into normal clinical findings.
3. Keep diagnosis suppression, evidence provenance, and nurse review gates active.
==============================================================`.trim();
};
