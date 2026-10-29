import {
  Brain,
  Bug,
  Cloud,
  Dog,
  Droplet,
  Gauge,
  Hand,
  HeartCrack,
  Microscope,
  Scan,
  Stethoscope,
  Syringe,
  Thermometer,
  UserRound,
  Utensils,
  Waves,
  Wind,
  type LucideIcon,
} from "lucide-react";

import type { PhotoCredit } from "@/components/landing/photo-credits";

/**
 * Ảnh cho dòng chủ đề sức khỏe trên trang chủ.
 *
 * Mọi ảnh lấy từ Wikimedia Commons với giấy phép cho phép dùng lại (public
 * domain, CC0, CC BY, CC BY-SA) và được ghi công ngay trên trang. Quy tắc chọn:
 * ảnh phải đúng với chủ đề (vật trung gian, dụng cụ, cách phòng bệnh hoặc chính
 * tác nhân dưới kính hiển vi), và không có người nhận diện được gắn với tên một
 * bệnh — gắn khuôn mặt một người thật với "trầm cảm" hay "lao" là xâm phạm họ.
 * Ảnh chỉ được thu nhỏ và nén lại, không chỉnh sửa nội dung.
 */
export interface HealthTopicPhoto {
  src: string;
  /** Mô tả đúng điều có trong ảnh, không phải tuyên bố y khoa. */
  alt: string;
  /** `object-position` khi ảnh ngang bị cắt vào khung dọc. */
  focus?: string;
  credit: PhotoCredit;
}

const CC_BY_2 = "https://creativecommons.org/licenses/by/2.0";
const CC_BY_3 = "https://creativecommons.org/licenses/by/3.0";
const CC0 = "https://creativecommons.org/publicdomain/zero/1.0/";
const COMMONS = "https://commons.wikimedia.org/wiki/File:";

export const HEALTH_TOPIC_PHOTOS: Record<string, HealthTopicPhoto> = {
  "sot-xuat-huyet-dengue": {
    src: "/health-topics/sot-xuat-huyet-dengue.webp",
    alt: "Muỗi vằn Aedes albopictus đang đốt trên da người",
    focus: "55% 50%",
    credit: { author: "James Gathany, CDC", license: "Public domain", licenseUrl: null, sourceUrl: `${COMMONS}Aedes_Albopictus.jpg` },
  },
  "cum-mua": {
    src: "/health-topics/cum-mua.webp",
    alt: "Một người đang được tiêm vắc xin cúm vào bắp tay",
    focus: "45% 40%",
    credit: { author: "NIAID", license: "CC BY 2.0", licenseUrl: CC_BY_2, sourceUrl: `${COMMONS}FluShot_(37127923433).jpg` },
  },
  "tay-chan-mieng": {
    src: "/health-topics/tay-chan-mieng.webp",
    alt: "Đôi tay đang rửa với xà phòng dưới vòi nước",
    focus: "62% 50%",
    credit: {
      author: "USDA",
      license: "Public domain",
      licenseUrl: null,
      sourceUrl: `${COMMONS}150th_Anniversary_of_U_S_Department_of_Agriculture-Historical_imagery_(20120106-OC-AMW-0074).jpg`,
    },
  },
  "tang-huyet-ap": {
    src: "/health-topics/tang-huyet-ap.webp",
    alt: "Máy đo huyết áp điện tử hiển thị chỉ số 140 trên 114",
    credit: {
      author: "YitzhakNat",
      license: "CC0",
      licenseUrl: CC0,
      sourceUrl: `${COMMONS}High_diastolic_blood_pressure_measurement_of_a_person_who_stood_up_after_waking_up.jpg`,
    },
  },
  "dai-thao-duong-type-2": {
    src: "/health-topics/dai-thao-duong-type-2.webp",
    alt: "Đôi tay đang đo đường huyết bằng máy và que thử",
    focus: "40% 55%",
    credit: {
      author: "Biswarup Ganguly",
      license: "CC BY 3.0",
      licenseUrl: CC_BY_3,
      sourceUrl: `${COMMONS}Blood_Glucose_Testing_-_Kolkata_2011-07-25_3981.JPG`,
    },
  },
  "sot-ret": {
    src: "/health-topics/sot-ret.webp",
    alt: "Muỗi Anopheles stephensi đang hút máu trên da người",
    focus: "45% 50%",
    credit: { author: "Jim Gathany, CDC", license: "Public domain", licenseUrl: null, sourceUrl: `${COMMONS}Anopheles_stephensi.jpeg` },
  },
  "lao-phoi": {
    src: "/health-topics/lao-phoi.webp",
    alt: "Vi khuẩn lao Mycobacterium tuberculosis dưới kính hiển vi điện tử, phối màu cam",
    credit: {
      author: "NIAID",
      license: "CC BY 2.0",
      licenseUrl: CC_BY_2,
      sourceUrl: `${COMMONS}Mycobacterium_Tuberculosis_Bacteria,_the_Cause_of_TB_(52766648105).jpg`,
    },
  },
  "viem-gan-b": {
    src: "/health-topics/viem-gan-b.webp",
    alt: "Các hạt virus viêm gan B dưới kính hiển vi điện tử, phối màu cam trên nền xanh",
    focus: "40% 50%",
    credit: { author: "NIAID", license: "CC BY 2.0", licenseUrl: CC_BY_2, sourceUrl: `${COMMONS}Hepatitis_B_Virus_(52443792486).jpg` },
  },
  "dot-quy": {
    src: "/health-topics/dot-quy.webp",
    alt: "Bàn tay người cao tuổi nắm cây gậy chống bằng gỗ",
    credit: {
      author: "Shixart1985",
      license: "CC BY 2.0",
      licenseUrl: CC_BY_2,
      sourceUrl: `${COMMONS}Elderly_person_holding_a_wooden_cane_while_standing_near_a_rustic_background_during_daytime.jpg`,
    },
  },
  "hen-phe-quan": {
    src: "/health-topics/hen-phe-quan.webp",
    alt: "Bàn tay cầm bình xịt hen trước tán lá xanh",
    focus: "45% 50%",
    credit: { author: "NIAID", license: "CC BY 2.0", licenseUrl: CC_BY_2, sourceUrl: `${COMMONS}Asthma_Inhaler_(29172634251).jpg` },
  },
  "benh-phoi-tac-nghen-man-tinh": {
    src: "/health-topics/benh-phoi-tac-nghen-man-tinh.webp",
    alt: "Dụng cụ tập thở với ba quả bóng màu trong ống trong suốt",
    credit: {
      author: "Nizzan Cohen",
      license: "CC BY 4.0",
      licenseUrl: "https://creativecommons.org/licenses/by/4.0",
      sourceUrl: `${COMMONS}Exercise_incentive_spirometer_02.jpg`,
    },
  },
  "tieu-chay-cap": {
    src: "/health-topics/tieu-chay-cap.webp",
    alt: "Bình lọc nước gốm dùng trong gia đình để có nước uống sạch",
    credit: {
      author: "Nabunje Leticia",
      license: "CC BY-SA 4.0",
      licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0",
      sourceUrl: `${COMMONS}Old_Ceramic_Water_Filter.jpg`,
    },
  },
  soi: {
    src: "/health-topics/soi.webp",
    alt: "Một hạt virus sởi dưới kính hiển vi điện tử, phối màu đỏ trên nền xanh",
    focus: "45% 60%",
    credit: { author: "NIAID, CDC", license: "Public domain", licenseUrl: null, sourceUrl: `${COMMONS}Measlesvirus.jpg` },
  },
  "benh-dai": {
    src: "/health-topics/benh-dai.webp",
    alt: "Một chú chó nhỏ đi trên đường phố Hội An",
    focus: "58% 50%",
    credit: { author: "Stan", license: "CC BY 2.0", licenseUrl: CC_BY_2, sourceUrl: `${COMMONS}Hoi_An_Street_Dog.jpg` },
  },
  "ngo-doc-thuc-pham": {
    src: "/health-topics/ngo-doc-thuc-pham.webp",
    alt: "Rau củ được rửa dưới vòi nước chảy trong bồn rửa",
    focus: "35% 50%",
    credit: {
      author: "Tracey Nicholls, CSIRO",
      license: "CC BY 3.0",
      licenseUrl: CC_BY_3,
      sourceUrl: `${COMMONS}CSIRO_ScienceImage_2709_Cleaning_Vegies_in_Running_Water.jpg`,
    },
  },
  "tram-cam": {
    src: "/health-topics/tram-cam.webp",
    alt: "Một chiếc lá đỏ nằm một mình trên ghế công viên ướt",
    focus: "50% 55%",
    credit: { author: "Michael Pardo", license: "CC0", licenseUrl: CC0, sourceUrl: `${COMMONS}Autumn_Seating_(23323012764).jpg` },
  },
};

export function photoForTopic(slug: string): HealthTopicPhoto | undefined {
  return HEALTH_TOPIC_PHOTOS[slug];
}

/** Biểu tượng thay ảnh cho chủ đề backend có nhưng chưa được chọn ảnh. */
const FALLBACK_ICONS: Array<[string, LucideIcon]> = [
  ["sot-xuat-huyet", Bug],
  ["cum", Thermometer],
  ["tay-chan-mieng", Hand],
  ["huyet-ap", Gauge],
  ["dai-thao-duong", Droplet],
  ["sot-ret", Microscope],
  ["lao", Scan],
  ["viem-gan", Syringe],
  ["dot-quy", Brain],
  ["hen", Wind],
  ["phoi", Cloud],
  ["tieu-chay", Waves],
  ["soi", UserRound],
  ["dai", Dog],
  ["ngo-doc", Utensils],
  ["tram-cam", HeartCrack],
];

export function fallbackIconForTopic(slug: string): LucideIcon {
  return FALLBACK_ICONS.find(([fragment]) => slug.includes(fragment))?.[1] ?? Stethoscope;
}
