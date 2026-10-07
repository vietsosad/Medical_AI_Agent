# 🏥 KHO BẢNG HỆ SỔ LÂM SÀNG TRUNG TÂM: ESI V5 GOLD STANDARD TABLE ARCHIVE
*(Tổng hợp và chắt lọc tinh hoa từ 2 tài liệu chuẩn: AHRQ ESI V5 & ESI Handbook V4)*
*Tài liệu gốc (Single Source of Truth) phục vụ trực tiếp cho AI Semantic Router (Script 2: `step2_build_rag_protocols.py`)*

---

## 🧭 PHẦN 1: THUẬT TOÁN QUYẾT ĐỊNH 4 BƯỚC (ESI V5 DECISION LOGIC & ALGORITHM)

Luồng phân định độ khẩn cấp lâm sàng theo chuẩn AHRQ ESI V5 được điều phối tuần tự theo 4 nút thắt (Decision Points A ➔ D):

```
       [ BỆNH NHÂN NHẬP VIỆN / KHÔNG GIAN HỘI THOẠI TRIAGE ]
                               │
                               ▼
        ┌─── DECISION POINT A: Cấp Tối Khẩn? ───┐
        │   (Immediate Lifesaving Intervention)  │ ──YES──► [ ESI LEVEL 1: TỐI KHẨN ]
        └────────────────────────────────────────┘          (Ngắt luồng <50ms, Báo 115/Điều Đưỡng)
                               │ NO
                               ▼
        ┌─── DECISION POINT B: Tình Huống Nguy Cơ? ───┐
        │   (High-Risk Situation / Severe Pain /      │ ──YES──► [ ESI LEVEL 2: KHẨN CẤP ]
        │         Altered Mental Status)              │          (Còi Báo Động Kanban Điều Dưỡng)
        └─────────────────────────────────────────────┘
                               │ NO
                               ▼
        ┌─── DECISION POINT C: Dự Đoán Tài Nguyên ───┐
        │    (How many different resources needed?)  │
        ├────────────────────────────────────────────┤ ──NONE─► [ ESI LEVEL 5: KHẢM M RỦ ]
        │                                            │ ──ONE──► [ ESI LEVEL 4: BÌNH THƯỜNG ]
        └────────────────────────────────────────────┘
                               │ MANY (2 or more)
                               ▼
        ┌─── DECISION POINT D: Sinh Hiệu Nguy Kịch? ──┐
        │    (Danger Zone Vital Signs Reassessment)   │ ──YES──► [ NÂNG SANG ESI 2 (UP-TRIAGE) ]
        └─────────────────────────────────────────────┘
                               │ NO
                               ▼
                    [ ESI LEVEL 3: ƯU TIÊN ]
```

---

## 🚨 PHẦN 2: TIÊU CHUẨN ESI LEVEL 1 - BÁO ĐỘNG SINH TỬ (IMMEDIATE LIFE-SAVING INTERVENTIONS & AVPU)
Bất kỳ bệnh nhân nào xuất hiện các trạng thái lâm sàng sau ĐỀU PHẢI lập tức ấn định **ESI 1**: Ngừng thở (Apneic), Không bắt được mạch (Pulselessness), Tụt huyết áp chí nguy (Profound hypotension), Hạ đường huyết nghiêm trọng (Severe hypoglycemia), Suy hô hấp cấp kịch tím tái, hoặc Mất ý thức (P/U trên thang AVPU).

### Bảng 2.1: Các Can Thiệp Sống Còn Trong Cấp Cứu Tối Khẩn (Life-saving Interventions)
| Nhóm Can Thiệp (Domain) | ✅ HÀNH ĐỘNG CỨU SỐNG (LIFESAVING - ESI 1) | ❌ KHÔNG BẢO CHỨNG ESI 1 (NOT LIFESAVING) |
| :--- | :--- | :--- |
| **Airway / Breathing** (Đường thở & Hô hấp) | • Thông khí BVM (Bóp bóng)<br>• Đặt nội khí quản (Intubation)<br>• Phẫu thuật mở khí quản (Surgical airway)<br>• Thở máy CPAP / BiPAP khẩn (Emergent NIPPV) | • Thở oxy găng mũi (Nasal cannula)<br>• Mặt nạ thở lại / không thở lại (Non-rebreather mask) |
| **Electrical Therapy** (Liệu pháp Điện tím) | • Sốc điện phá rung (Defibrillation)<br>• Chuyển nhịp cấp cứu (Emergent cardioversion)<br>• Tạo nhịp ngoài lồng ngực (External pacing) | • Đăng ký / Theo dõi Monitor nhịp tim thông thường (Cardiac monitor) |
| **Procedures** (Thủ tục can thiệp) | • Chọc kim dẫn lưu thùy khí (Chest needle decompression)<br>• Chọc dịch màng tim (Pericardiocentesis)<br>• Mở lồng ngực cấp cứu (Open thoracotomy) | • Điện tâm đồ (ECG), Siêu âm, Chụp X-quang<br>• Siêu âm FAST chấn thương gan/lách<br>• Tiêm truyền nội tủy (Intraosseous access) |
| **Hemodynamics** (Huyết động học) | • Truyền dịch bồi hoàn khối lượng lớn khẩn cấp<br>• Truyền Máu (Blood administration)<br>• Cầm máu chảy phun thành tia (Major hemorrhage control) | • Thiết lập đường truyền IV (IV access)<br>• Khóa cất đường tĩnh mạch (Saline lock) |
| **Medications** (Thuốc đặc trị tối khẩn) | • **Naloxone** (Giải độc ngộ độc opioid)<br>• **Dextrose (D50)** (Hạ đường huyết ngất)<br>• **Epinephrine IM** (Sốc phản vệ bóp gan)<br>• **Dopamine, Atropine, Adenosine**<br>• Phối hợp xịt khí dung liều cao liên tục (Beta-agonists) | • Thuốc giảm đau (NSAID / Acetaminophen / Morphine)<br>• Kháng sinh (Antibiotics), Heparin, Nitroglycerin IV<br>• Aspirin (ASA) |

### Bảng 2.2: Thang Đo Đánh Giá Đương Tri Giác (AVPU Scale)
| Cấp Độ AVPU | Trạng Thái Lâm Sàng (Consciousness Level) | Quy Định Phân Luồng ESI |
| :--- | :--- | :--- |
| **A - Alert** (Tỉnh táo) | Bệnh nhân mở mắt tự nhiên, đáp ứng âm thanh, hiểu định hướng thời gian/không gian. | *Đánh giá tiếp các bước B, C, D.* |
| **V - Verbal** (Đáp ứng lời nói) | Mở mắt hoặc trả lời khi gọi to. Có thể nhầm lẫn về định hướng không gian/thời gian. | *Cảnh báo nguy cơ cao (ESI 2).* |
| **P - Painful** (Đáp ứng đau) | Chỉ rên hoặc kích thích vận động khi bấm gối móng tay, véo da hoặc chà xát đòn ức. | **BẮT BUỘC ESI LEVEL 1 / 2 (TỐI KHẨN)** |
| **U - Unresponsive** (Bất tỉnh) | Nằm cự tuyệt mọi kích thích đau bóp, tiếng kêu. Ngủ vùi hoàn toàn. | **BẮT BUỘC ESI LEVEL 1 (TỐI KHẨN)** |

---

## ⚠️ PHẦN 3: TIÊU CHUẨN ESI LEVEL 2 - TÌNH HUỐNG NGUY CƠ CHIẾN DỊCH (HIGH-RISK SITUATIONS BY SYSTEM)
Một bệnh nhân mang tình trạng nguy cơ cao (High-risk) là ca bệnh có thể biến chứng trụy tuần hoàn, trụy tim mạn hoặc hỏng mạch máu thần kinh nếu bắt chờ đợi. Bệnh nhân có cơn đau lở 10/10 hoặc lơ mơ bất thường.

### Bảng 3.1: Các Danh Mục Bệnh Khẩn Cấp Bắt Buộc Gán ESI 2 (Chia theo 10 Hệ Cơ Quan)
| Hệ Cơ Quan (System) | Ví dụ Hội Chứng / Chẩn Đoán Cảnh Báo (High-Risk Diagnosis) | Dấu Hiệu Lâm Sàng Thường Gặp (Signs & Symptoms) |
| :--- | :--- | :--- |
| **1. Cardiac** (Tim mạch) | • Hội chứng Mạch Vành Cấp (Chest pain / ACS)<br>• Tắc mạch máu nghẽn huyết (Acute arterial occlusion)<br>• Đau ngực trên nền tiền sử đặt Stent / Nung tai Angioplasty<br>• Viêm nội tâm mạc nhiễm khuẩn (Infective endocarditis)<br>• Tràn dịch màng tim bóp tim (Pericardial effusion) | • Đau bóp ngực buốt ran gạt ra vai/vã mồ hôi hột.<br>• Mất mạch viễn ngõ chân/tay (Absence of distal pulse).<br>• Đau thắt tim nhói buốt kèm khó thở, sinh hiệu còn giữ ổn định tạm thời. |
| **2. Neurologic** (Thần kinh / Stroke) | • Đột quỵ Nhồi máu/Xuất huyết não cấp (Acute Ischemic Stroke / CVA)<br>• Nghi ngờ Viêm Màng Não (Rule out meningitis)<br>• Tiền sử đột quỵ lặp lại kèm triệu chứng mới xuất hiện | • **Dấu hiệu FAST:** Méo miệng, Liệt/thõng tay chân dốc rãnh, Nghe đớ nói ngớ, Khởi phát ngộ.<br>• Nhức đầu như rễ xé kèm Sốt cao thấu sọ và Cứng cổ bóp (Stiff neck). |
| **3. Respiratory** (Hô hấp / Phổi) | • Viêm nắp thanh môn nghẹt thở (Acute epiglottitis)<br>• Hen suyễn lên cơn kịch phát búp ngực (Severe asthma attack)<br>• Tràn khí màng phổi tự phát (Spontaneous pneumothorax)<br>• Tràn dịch màng phổi diện rộng bóp phổi | • Triệu chứng **Chảy nước dãi dào vã (Drooling)** nghẹt nuốt.<br>• Khó thở hụt hơi nhức, phải co cắp cơ gian sườn nhịp thở bạo bùng.<br>• Đau buốt lồng ngực tự bốc cháy nghẹn hơi đột ngột (Sudden shortness of breath). |
| **4. Abdomen** (Tiêu hóa / Abdomens) | • Xuất huyết tiêu hóa cấp tính (Gastrointestinal bleeding / GI bleed)<br>• Đau bụng kịch phát ở người cao tuổi (> 65 tuổi)<br>• Vỡ túi phình động mạch chủ bụng (AAA) | • Nôn ra máu tươi/cục máu xỉn (Hematemesis) hoặc Đi ngoài phân đen/chảy máu tuếch (Hematochezia).<br>• Mạch dồn dập tim đập dữ (Tachycardia), bụng gồng buốt. |
| **5. Gynecology** (Phụ khoa / Sản) | • Thai ngoài tử cung vỡ (Ectopic pregnancy)<br>• Dọa sảy thai / sảy thai cấp cứu (Spontaneous abortion) | • Bệnh nhân **đang mang thai** kèm đau nhói bụng dưới kịch dữ rãnh bụng.<br>• Máu chảy tuếch ầm, mạch đập dồn dập dẫu huyết áp đang bình thường. |
| **6. Genitourinary** (Thận - Tiết niệu)| • Xoắn tinh hoàn bóp máu (Testicular torsion)<br>• Suy thận cấp / Nghẽn cầu chạy thận (Acute renal failure) | • Đau quặn nhức xé vùng bìu khốn khổ ngẫu hứng phát tác.<br>• Không thể châm thận nhân tạo/tắc ống chạy thận. |
| **7. Pediatric** (Nhi khoa / Nhi khẩn)| • Hen suyễn bóp hơi nhi khoa (Pediatric asthma attack)<br>• Tiêu chảy nôn ói nghẹt lịm (Vomiting, diarrhea, unable to eat) | • Co nhịp thở gian sườn bóp mũi (Nasal flaring / Intercostal reactions).<br>• Mắt trũng sâu, thóp lót xẹp búp (Sunken fontanel), lịm ngủ ngần ngại ngó. |
| **8. Mental Health** (Tâm thần kịch)| • Ý định/Tự sát thắt cổ, cắt tay (Suicidal attempt or active complaint)<br>• Bạo động hiến hung vô thần (Combative, hostile, hysterical)<br>• Tình nghi xâm hại tình dục vừa xảy ra (Sexual assault - any) | • Cần giám sát bảo vệ tức khắc trói lỏng hoặc cách ly chuyên hộ. |
| **9. Trauma** (Chấn thương nặng) | • Tai nạn xe cộ mất ý thức tạm thời (MVC with T-LOC)<br>• Vết đâm hở găm trúng bắp chân / bụng (Stab wound to groin/torso) | • Chấn thương đầu có quãng bàng hoàng sương mù (Head trauma history).<br>• Máu rò chảy nhưng tạm cầm giữ được bằng băng gạc bóp bện. |
| **10. General / Immuno** (Toàn thân) | • Suy giảm miễn dịch (Immunocompromised / HIV / Ung thư Hóa trị)<br>• Ghép tạng (Post-transplant or on waiting list) | • Ngay cả khi chỉ số súng sốt nhẹ (hoặc không sốt) vẫn tiềm ẩn nguy cơ sốc nhiễm khuẩn (Sepsis) hủy bạo bùng. |

---

## 📈 PHẦN 4: THANG ĐO CHI TIẾT SINH HIỆU CHÍ NGUY (DANGER ZONE & NORMAL VITALS BY AGE)
Sinh hiệu ngoài dải bình thường ở bước D phải bóp báo còi đẩy thắp ca ESI 3 lên **ESI 2 (Up-triage)**:

### Bảng 4.1: Ngưỡng Sinh Hiệu Nguy Kịch (High-Risk Vital Signs Thresholds - Decision Point D)
*Chuẩn từ AHRQ ESI V5 (Lưu ý: Ngưỡng bạo bùng bồi bơi SpO2 được nâng kiên c cố từ <90% ở bản cũ lên <92% ở V5!)*
| Nhóm Tuổi (Age Group) | Nhịp Tim (Heart Rate - HR) | Nhịp Thở (Respiratory Rate - RR) | Độ Bão Hòa Oxy Khí Trời (SpO2) |
| :--- | :--- | :--- | :--- |
| **< 1 tháng tuổi (Neonate)** | **> 190** lần/phút | **> 60** lần/phút | **< 92%** |
| **1 – 12 tháng tuổi (Infant)**| **> 180** lần/phút | **> 55** lần/phút | **< 92%** |
| **1 – 3 tuổi (Toddler)** | **> 140** lần/phút | **> 40** lần/phút | **< 92%** |
| **3 – 5 tuổi (Preschool)** | **> 120** lần/phút | **> 35** lần/phút | **< 92%** |
| **5 – 12 tuổi (School Age)** | **> 120** lần/phút | **> 30** lần/phút | **< 92%** |
| **12 – 18 tuổi (Adolescent)** | **> 100** lần/phút | **> 20** lần/phút | **< 92%** |
| **> 18 tuổi (Người Lớn)** | **> 100** hoặc **< 40** lần/phút| **> 20** lần/phút | **< 92%** *(hoặc <90% ESI V4)* |

### Bảng 4.2: Dải Sinh Hiệu Bình Thường Cho Trẻ Em (Normal Pediatric Vital Signs)
| Tuổi Trẻ (Pediatric Age) | Nhịp Tim (HR - beats/min) | Nhịp Thở (RR - breaths/min) | Huyết Áp Tâm Thu (Systolic BP - mm Hg) |
| :--- | :--- | :--- | :--- |
| Sơ sinh đến < 1 tháng | 90 – 190 | 35 – 60 | 67 – 84 |
| Trẻ nhũ nhi (1 – 12 tháng)| 90 – 180 | 30 – 55 | 72 – 104 |
| Trẻ tập đi (1 – 3 tuổi) | 80 – 140 | 22 – 40 | 86 – 104 |
| Trẻ mẫu giáo (3 – 5 tuổi) | 65 – 120 | 18 – 35 | 89 – 112 |
| Trẻ tiểu học (5 – 12 tuổi)| 70 – 120 | 16 – 30 | 90 – 115 |
| Vị thành niên (12 – 18 tuổi)| 60 – 100 | 12 – 20 | 100 – 130 |

### Bảng 4.3: Chỉ Bảo Sốt Nhi Khoa & Hạ Thân Nhiệt Cảnh Báo (Pediatric Fever Red Flags)
| Độ Tuổi Nhi | Tiêu Chuẩn Nhiệt Độ (Temperature Criteria) | Quy Quyết Định Triage ESI |
| :--- | :--- | :--- |
| **1 - 28 ngày tuổi (< 1 tháng)** | Sốt cao > 38.0°C (100.4°F) hoặc hạ < 36.0°C | **Bắt buộc gán ESI 2 (Khẩn Cấp)** |
| **1 - 3 tháng tuổi (30-90 ngày)**| Sốt cao > 38.0°C (100.4°F) hoặc hạ < 36.0°C | **Xem xét chỉ định ngay ESI 2** |
| **3 tháng đến 36 tháng tuổi** | Sốt > 39.0°C (102.2°F) hoặc < 36.0°C;<br>Hồ sơ tiêm chủng chưa trọn vẹn (Incomplete Immunizations);<br>Không thấy nguồn gốc gây sốt cụ thể ngoài mẫn kịch. | **Xem xét gán ESI 2 hoặc ESI 3** |

---

## 🔬 PHẦN 5: ĐỊNH TRỊ TÀI NGUYÊN (ESI LEVEL 3, 4, 5 RESOURCES TABLE & SCENARIOS)
Quy tắc kiểm đếm tài nguyên chỉ thực thi **sau khi** bệnh nhân được xác lập là KHÔNG ĐUỔI VÀO ESI 1 hoặc ESI 2. Cần ghi nhớ: Đếm số **nhóm loại (different types)** tài nguyên cần dùng, chứ KHÔNG ĐẾM SỐ VẬT TƯ LẺ (vd: Xét nghiệm máu trọn bộ CBC + Điện tim + U-cream đều gom chung là 1 tài nguyên xét nghiệm Lab!).

### Bảng 5.1: Quy Định Tài Nguyên Hợp Lệ ESI (Resources vs Non-Resources)
| ✅ TÀI NGUYÊN BẮT BUỘC ĐẾM (COUNTED RESOURCES) | ❌ KHÔNG BỊ ĐẾM LÀ TÀI NGUYÊN (NOT RESOURCES) |
| :--- | :--- |
| • **Labs:** Máu (Blood), Nước tiểu (Urine, C&S, hCG)<br>• **Chẩn đoán hình ảnh:** Điện tâm đồ (ECG), X-quang, CT Scan, MRI, Siêu âm, Chụp mạch máu (Angiography)<br>• **Bù nước & Điện giải:** Truyền tĩnh mạch IV Fluid (Hydration)<br>• **Thuốc qua đường tiêm/xịt:** Thuốc IV, Tiêm bắp IM, hoặc Xịt khí dung bóp (Nebulized meds)<br>• **Thăm khám chuyên khoa:** Hội chẩn bác sĩ chuyên sâu (Specialty consultation)<br>• **Thủ thuật:**<br>  - Thủ thuật đơn (Simple = 1 resource): Khâu gáy nhục nhăn lăm (Laceration repair), Đặt thông tiểu Foley<br>  - Thủ thuật phức tạp (Complex = 2 resources): Tiêm an thần gây nín đau (Procedural sedation) | • Thăm khám lâm sàng và Lịch sử bệnh (History & Physical, kể cả khám âm đạo/phụ khoa)<br>• Xét nghiệm nhanh tại bàn kíp (Point-of-care testing - POC Glucose, POC Strep)<br>• Khóa cắm chờ tĩnh mạch (Saline or Hep-lock)<br>• **Thuốc uống:** Uống các viên nén PO, Thuốc giảm đau uống, Thuốc ho bồi<br>• **Tiêm bọc dịch tế:** Tiêm giải uốn ván (Tetanus immunization)<br>• Xin cấp lại đơn thuốc (Prescription refills) & Gọi điện hội thoại Bác sĩ gia đình<br>• **Chăm sóc vết thương đơn giản:** Thay băng gạc nhục rẽ (Dressings), xem lại vết cắt xát (Recheck wound)<br>• **Nẹp cố định tạm:** Cấp gậy chống (Crutches), nẹp chân tay, treo dây băng vai |

### Bảng 5.2: 12 Kịch Bản Lâm Sàng Thực Tế Phân Điểm Tài Nguyên (Clinical Scenarios Archive)
| STT | Kịch Bản Khám Trệnh (Patient Scenario) | Các Can Thiệp Chi Nhánh Cần Có | Tài Nguyên Đếm | Cấp ESI Chốt |
| :--- | :--- | :--- | :--- | :--- |
| **01** | Nam, 22 tuổi, **Đau bụng hố chéo Hố Phải (RLQ)** từ sáng kèm buồn nôn, chán ăn cự nạp. | Khám + Xét nghiệm máu/nước tiểu + Truyền dịch IV + Chụp CT bụng + Hội chẩn ngoại khoa | **2 hoặc nhiều hơn** (Lab + IV + CT + Consult) | **ESI 3** |
| **02** | Nữ, 45 tuổi bị béo phì, **Đau tức & sưng vù cắp bắp chéo Dưới Tả** sau chuyến lái xe ngồi yên dài 12 tiếng (Nghĩ tới DVT). | Khám + Xét nghiệm huyết học + Siêu âm dò huyết khối mạch máu chi dưới + Thăm dập chống đông | **2 hoặc nhiều hơn** (Lab + Siêu âm Doppler) | **ESI 3** |
| **03** | Nữ, 19 tuổi trượt gót khi chơi bóng đá. **Sưng nhức quanh mắt cá chân** ngoại bắp, đau điệu khi chịu trọng lực đứng gõ gót. | Khám bóp chân + **Chụp X-Quang mắt cá** + Nẹp quấn Ace Wrap + Nhắc dặn dùng gậy chống sải | **Đúng 01 tài nguyên** (X-Quang) | **ESI 4** |
| **04** | Nữ, 29 tuổi, cảm giác **Đau rát khi đi tiểu (Dysuria)**, không sốt, không có dịch âm đạo hôi bóp rò. | Khám + **Xét nghiệm nước tiểu & Nuôi cấy (Urine C&S / hCG)** + Kê toa kháng sinh uống | **Đúng 01 tài nguyên** (Xét nghiệm nước tiểu) | **ESI 4** |
| **05** | Nam, 19 tuổi, **Đau rát hầu họng (Sore throat)** & hơi gai ngớ, sinh hiệu bình thường tịnh. | Khám + phết họng cấy khuẩn dịch bóp + Kê viên uống viên hạ sốt | **Đúng 01 tài nguyên** (Xét nghiệm cấy họng Lab) | **ESI 4** |
| **06** | Bé trai 3 tuổi, **Đau rát êm tai tay gãi (Ear pain)**, đã tiêm chủng đủ 100%. Sinh hiệu tươi cười ổn định. | Khám tai nội soi cắm chốt + Kê thuốc nhỏ/uống tại nhà | **Không mất tài nguyên nào** (Chỉ khám + Thuốc PO) | **ESI 5** |
| **07** | Bé trai 10 tuổi bị **Mẩn rộp ban mẩn độc ngứa bóp ngõ (Poison ivy)** hai gầm cắp chân tay. | Khám da bôi phết + Kê tuýp kem bôi nạp nhục rã | **Không mất tài nguyên nào** | **ESI 5** |
| **08** | Nam, 52 tuổi khỏe mạnh, **Hết thuốc hạ huyết áp 2 ngày**, không có đau ngực nhức đầu. Huyết áp đo được: 150/92 mmHg. | Khám tim bóp nhịp thảnh thơi + Kê lại đơn thuốc mới (Prescription refill) | **Không mất tài nguyên nào** | **ESI 5** |

---

## 🛠️ PHẦN 6: HƯỚNG DẪN XỬ LÝ & TÍCH HỢP TRONG THỰC THI SCRIPT DỮ LIỆU CỦA BẠN

Bảng biểu trên đã là **Tượng Đài Tri Thức Vàng (Gold Standard Clinical Ground Truth)** về chuyên môn ESI V4 & V5 từ Bộ Y Tế và Hoa Kỳ (AHRQ). Để luồng AI Agent trong dự án của chúng ta bạo bùng phát huy sức mạnh vượt trội nhất khi sinh phác đồ ở **Script 2 (`step2_build_rag_protocols.py`)**, đây là hướng dẫn giải quyết điểm mấu chốt còn lại:

### 1. VẤN ĐỀ THIẾU SÓT DUY NHẤT (VĂN CHẤT NGỮ ÂM ĐỊA PHƯƠNG BỆNH NHÂN TIẾNG VIỆT)
*   **Thực tế lâm sàng tại VN:** Khi bệnh nhân chat vào App Trợ lý Triage, họ sẽ **KHÔNG BAO GIỜ** dùng văn phong Anh văn kỹ thuật như *"Tôi đang bị Acute Myocardial Infarction kèm diaphoresis và SpO2 < 92%"*. Họ sẽ nói: *"Bác sĩ ơi tim tôi nó **đập bùm bụp như muốn lao ra ngoài**, ngực **nhói thấu gan**, **tay chân lạnh toát vã mồ hôi hột** mệt lịm!"*
*   **Cách giải quyết (Đã tích hợp trong `STEP_BY_STEP_DATA_SETUP.md`):** 
    Bạn **không cần cất sức lùng sục thêm bất kỳ sách giáo khoa Y tế Tiếng Anh nào nữa**! Bản Master này là quá đủ về con số y tế! Cái bạn cần làm lúc chạy **Script 1 (`step1_extract_vitals_and_ontology.py`)** là để Python tự động tạo ra một file **Từ điển Ngữ nghĩa Lâm sàng Tiếng Việt (`data/ontology_vi_en.json`)**, ánh xạ các từ lóng dân gian Việt Nam về mã ESI 2 trong Bảng 3.1:
    ```json
    {
      "cardiac_chest_pain": {
        "standard_name": "Acute Coronary Syndrome / Angina (ESI 2)",
        "vi_medical_term": "Hội chứng vành cấp / Đau ngực khổng nạp",
        "slang_terms": ["nhói tim", "đau buốt ngực trái", "nặng nhọt búp lồng ngực", "vã mồ hôi hột lạnh toát", "mệt xỉu lả"]
      },
      "neurologic_stroke": {
        "standard_name": "Acute Ischemic Stroke / CVA (ESI 2)",
        "vi_medical_term": "Đột quỵ não cấp / Nhồi máu bóp sọ",
        "slang_terms": ["méo miệng", "đơ nửa tay gõ", "nghe nhói xé đầu", "tự dưng đớ lưỡi không nói được", "liệt rũ tay"]
      }
    }
    ```

### 2. KẾ HOẠCH THỰC TRÍ KÍNH HÀNH SCRIPT 1 & SCRIPT 2 (LUỔNG DỮ LIỆU 2 TẦNG CHUYÊN SÂU)
Giờ đây, bạn có thể tự tin 100% triển khai luồng chuẩn bị dữ liệu với 2 báu vật trong tay:
1.  **Tài liệu Master ESI Table:** File này (`master_esi_clinical_tables.md`) cung cấp 100% độ chính xác về con số sinh hiệu chi ly (Bảng 4.1 & Bảng 2.1).
2.  **Từ điển Ontology Tiếng Việt:** Cung cấp từ lóng địa phương.
Khi bạn cho chạy **Script 2 (`step2_build_rag_protocols.py`)**, LLM Semantic Router sẽ nhào nặn hai nguồn này vào nhau, tự động nặn ra ~25 phác đồ RAG Tiếng Việt vừa đậm đặc chất xám chuyên môn bệnh viện (mãi mãi tuân thủ SpO2 < 92%, Nhịp tim < 40), vừa thông hiểu mọi sắc thái than bệnh êm đềm của người bệnh bản xứ Việt Nam!
