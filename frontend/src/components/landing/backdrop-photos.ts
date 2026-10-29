import type { CreditedPhoto, PhotoCredit } from "@/components/landing/photo-credits";

/**
 * Ảnh cho bức tường ảnh phía sau đầu trang chủ (HeroBackdrop). Hai nền động bên
 * dưới (EvidenceBackdrop, CareLoopBackdrop) chỉ vẽ bằng nét, không dùng ảnh.
 *
 * Cùng quy tắc với ảnh chủ đề sức khỏe (health-topic-photos.ts): chỉ lấy từ
 * Wikimedia Commons với giấy phép cho phép dùng lại, ghi công ngay trên trang (ở
 * chân trang), ảnh chỉ được thu nhỏ và nén lại. Thêm hai điều cho ảnh nền:
 * không có khuôn mặt nhận diện được, và không có biển tên cơ sở nào đọc được ở
 * cỡ ô ảnh -- ảnh nền không được ngầm nói rằng sản phẩm hợp tác với nơi đó. Ảnh
 * có logo hãng hoặc dấu ngày của máy ảnh cũng bị loại.
 */
export interface BackdropPhoto {
  src: string;
  /** Ảnh chụp gì. Ảnh nền là trang trí (alt rỗng), nên mô tả chỉ dùng cho dòng ghi công. */
  label: string;
  /** Ô trên tường: ảnh ngang nằm ô thấp, ảnh đứng nằm ô cao. */
  shape: "wide" | "square" | "tall";
  /** `object-position` khi ảnh bị cắt vào ô. */
  focus?: string;
  credit: PhotoCredit;
}

const CC_BY_2 = "https://creativecommons.org/licenses/by/2.0";
const CC_BY_SA_2 = "https://creativecommons.org/licenses/by-sa/2.0";
const CC_BY_SA_3 = "https://creativecommons.org/licenses/by-sa/3.0";
const CC_BY_SA_4 = "https://creativecommons.org/licenses/by-sa/4.0";
const CC0 = "https://creativecommons.org/publicdomain/zero/1.0/";
const COMMONS = "https://commons.wikimedia.org/wiki/File:";

export const BACKDROP_PHOTOS = {
  "tram-y-te-doi": {
    src: "/landing/backdrop/tram-y-te-doi.webp",
    label: "Trạm y tế xã Sơn Trung",
    shape: "wide",
    credit: { author: "Dinh Ngoc Binh", license: "CC BY-SA 3.0", licenseUrl: CC_BY_SA_3, sourceUrl: `${COMMONS}Trạm_y_tế_xã_Sơn_Trung_-_panoramio.jpg` },
  },
  "tram-y-te-trang": {
    src: "/landing/backdrop/tram-y-te-trang.webp",
    label: "Trạm y tế xã Sơn Bình",
    shape: "square",
    focus: "50% 60%",
    credit: { author: "Dinh Ngoc Binh", license: "CC BY-SA 3.0", licenseUrl: CC_BY_SA_3, sourceUrl: `${COMMONS}Trạm_y_tế_xã_Sơn_Bình_-_panoramio.jpg` },
  },
  "benh-vien-ninh-thuan": {
    src: "/landing/backdrop/benh-vien-ninh-thuan.webp",
    label: "Cổng bệnh viện tỉnh Ninh Thuận",
    shape: "wide",
    focus: "50% 70%",
    credit: { author: "Windrain", license: "CC BY-SA 4.0", licenseUrl: CC_BY_SA_4, sourceUrl: `${COMMONS}Bệnh_viện_tỉnh_Ninh_Thuận.jpg` },
  },
  "hanh-lang": {
    src: "/landing/backdrop/hanh-lang.webp",
    label: "Hành lang bệnh viện",
    shape: "tall",
    credit: { author: "W.carter", license: "CC0", licenseUrl: CC0, sourceUrl: `${COMMONS}Corridor_on_the_second_level_-_NÄL_hospital_2.jpg` },
  },
  "phong-mo": {
    src: "/landing/backdrop/phong-mo.webp",
    label: "Phòng mổ",
    shape: "square",
    credit: { author: "Dr.jayesh amin", license: "CC BY-SA 3.0", licenseUrl: CC_BY_SA_3, sourceUrl: `${COMMONS}Laparoscopic_operating_theatre.jpg` },
  },
  "may-theo-doi": {
    src: "/landing/backdrop/may-theo-doi.webp",
    label: "Máy theo dõi bệnh nhân ở phòng cấp cứu",
    shape: "tall",
    focus: "38% 40%",
    credit: {
      author: "Tony Webster",
      license: "CC BY-SA 2.0",
      licenseUrl: CC_BY_SA_2,
      sourceUrl: `${COMMONS}Emergency_Room_(18359923719).jpg`,
    },
  },
  "nhiet-ke-dien-tu": {
    src: "/landing/backdrop/nhiet-ke-dien-tu.webp",
    label: "Nhiệt kế điện tử",
    shape: "wide",
    credit: { author: "Jacek Halicki", license: "CC BY-SA 4.0", licenseUrl: CC_BY_SA_4, sourceUrl: `${COMMONS}2023_Elektroniczny_termometr_lekarski.jpg` },
  },
  "may-do-spo2": {
    src: "/landing/backdrop/may-do-spo2.webp",
    label: "Máy đo SpO2 kẹp ngón tay",
    shape: "square",
    focus: "40% 50%",
    credit: { author: "Jakub T. Jankiewicz", license: "CC BY-SA 4.0", licenseUrl: CC_BY_SA_4, sourceUrl: `${COMMONS}Pulse_oximeter_on_a_finger.jpg` },
  },
  "ong-nghe-dien-tim": {
    src: "/landing/backdrop/ong-nghe-dien-tim.webp",
    label: "Ống nghe đặt trên băng điện tim",
    shape: "square",
    credit: { author: "Ivan2010", license: "CC BY-SA 4.0", licenseUrl: CC_BY_SA_4, sourceUrl: `${COMMONS}Objetos_medicos_de_uso_en_Cardiología.jpg` },
  },
  "ong-nghe": {
    src: "/landing/backdrop/ong-nghe.webp",
    label: "Ống nghe",
    shape: "wide",
    credit: { author: "Jacek Halicki", license: "CC BY-SA 4.0", licenseUrl: CC_BY_SA_4, sourceUrl: `${COMMONS}2023_Stetoskop.jpg` },
  },
  "dien-thoai-toi": {
    src: "/landing/backdrop/dien-thoai-toi.webp",
    label: "Điện thoại trong tay",
    shape: "tall",
    focus: "45% 50%",
    credit: { author: "Dennis Cortés", license: "CC0", licenseUrl: CC0, sourceUrl: `${COMMONS}Black_smartphone_in_hand_(Unsplash).jpg` },
  },
  "dien-thoai-sang": {
    src: "/landing/backdrop/dien-thoai-sang.webp",
    label: "Điện thoại màn hình sáng",
    shape: "square",
    focus: "62% 50%",
    credit: {
      author: "Santeri Viinamäki",
      license: "CC BY-SA 4.0",
      licenseUrl: CC_BY_SA_4,
      sourceUrl: `${COMMONS}Hand_holding_smartphone_with_blank_white_screen.jpg`,
    },
  },
  "nhiet-ke-tran": {
    src: "/landing/backdrop/nhiet-ke-tran.webp",
    label: "Nhiệt kế đo trán",
    shape: "square",
    focus: "30% 50%",
    credit: { author: "ajay_suresh", license: "CC BY 2.0", licenseUrl: CC_BY_2, sourceUrl: `${COMMONS}Digital_Thermometer_(51825721879).jpg` },
  },
  "dieu-duong": {
    src: "/landing/backdrop/dieu-duong.webp",
    label: "Nhân viên y tế ghi chép",
    shape: "tall",
    focus: "50% 40%",
    credit: {
      author: "Shixart1985",
      license: "CC BY 2.0",
      licenseUrl: CC_BY_2,
      sourceUrl: `${COMMONS}Medical_professional_holding_a_glass_of_water_while_preparing_notes_in_a_clinical_setting.jpg`,
    },
  },
  "xe-cuu-thuong": {
    src: "/landing/backdrop/xe-cuu-thuong.webp",
    label: "Xe cứu thương ở TP. Hồ Chí Minh",
    shape: "square",
    focus: "55% 55%",
    credit: { author: "Syced", license: "CC0", licenseUrl: CC0, sourceUrl: `${COMMONS}Ambulance_in_Saigon_near_district_4_hospital.jpg` },
  },
  "pho-nha-thuoc": {
    src: "/landing/backdrop/pho-nha-thuoc.webp",
    label: "Nhà thuốc trên phố Quán Sứ, Hà Nội",
    shape: "wide",
    credit: { author: "Phan Minh Tuấn", license: "CC BY-SA 4.0", licenseUrl: CC_BY_SA_4, sourceUrl: `${COMMONS}Nhà_thuốc,_6_Quán_Sứ,_Hà_Nội_001.JPG` },
  },
} satisfies Record<string, BackdropPhoto>;

export type BackdropPhotoKey = keyof typeof BACKDROP_PHOTOS;

/** Dòng ghi công cho chân trang, theo thứ tự trên. */
export const BACKDROP_CREDITS: CreditedPhoto[] = Object.entries(BACKDROP_PHOTOS).map(([key, photo]) => ({
  key,
  label: photo.label,
  credit: photo.credit,
}));
