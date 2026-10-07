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

import { cn } from "@/lib/utils";

export type ArtworkKind =
  | "dengue"
  | "flu"
  | "hand-foot-mouth"
  | "hypertension"
  | "diabetes"
  | "malaria"
  | "tuberculosis"
  | "hepatitis"
  | "stroke"
  | "asthma"
  | "copd"
  | "diarrhea"
  | "measles"
  | "rabies"
  | "food-poisoning"
  | "depression"
  | "general";

interface HealthTopicArtworkProps {
  slug: string;
  name: string;
  compact?: boolean;
  decorative?: boolean;
  className?: string;
}

export function artworkKindForTopic(slug: string, name: string): ArtworkKind {
  const normalizedSlug = slug.toLocaleLowerCase("vi");
  const value = `${slug} ${name}`.toLocaleLowerCase("vi");

  if (normalizedSlug.includes("sot-xuat-huyet") || value.includes("dengue")) return "dengue";
  if (normalizedSlug.includes("cum-mua") || value.includes("flu")) return "flu";
  if (normalizedSlug.includes("tay-chan-mieng")) return "hand-foot-mouth";
  if (normalizedSlug.includes("tang-huyet-ap")) return "hypertension";
  if (normalizedSlug.includes("dai-thao-duong")) return "diabetes";
  if (normalizedSlug.includes("sot-ret")) return "malaria";
  if (normalizedSlug.includes("lao-phoi")) return "tuberculosis";
  if (normalizedSlug.includes("viem-gan")) return "hepatitis";
  if (normalizedSlug.includes("dot-quy")) return "stroke";
  if (normalizedSlug.includes("hen-phe-quan")) return "asthma";
  if (normalizedSlug.includes("phoi-tac-nghen") || value.includes("copd")) return "copd";
  if (normalizedSlug.includes("tieu-chay")) return "diarrhea";
  if (normalizedSlug === "soi") return "measles";
  if (normalizedSlug.includes("benh-dai")) return "rabies";
  if (normalizedSlug.includes("ngo-doc-thuc-pham")) return "food-poisoning";
  if (normalizedSlug.includes("tram-cam")) return "depression";
  return "general";
}

const artworkIcons: Record<ArtworkKind, LucideIcon> = {
  dengue: Bug,
  flu: Thermometer,
  "hand-foot-mouth": Hand,
  hypertension: Gauge,
  diabetes: Droplet,
  malaria: Microscope,
  tuberculosis: Scan,
  hepatitis: Syringe,
  stroke: Brain,
  asthma: Wind,
  copd: Cloud,
  diarrhea: Waves,
  measles: UserRound,
  rabies: Dog,
  "food-poisoning": Utensils,
  depression: HeartCrack,
  general: Stethoscope,
};

export function artworkIconForTopic(slug: string, name: string): LucideIcon {
  return artworkIcons[artworkKindForTopic(slug, name)];
}

const commonStroke = "stroke-slate-800 dark:stroke-slate-100";
const softStroke = "stroke-teal-700 dark:stroke-teal-300";
const accentFill = "fill-teal-100 dark:fill-teal-950";
const surfaceFill = "fill-white dark:fill-slate-900";

function ArtworkBackdrop() {
  return (
    <>
      <circle cx="238" cy="174" r="118" className={accentFill} />
      <path d="M74 102c18-20 39-32 64-38M350 272c23-8 42-22 57-42" fill="none" strokeLinecap="round" strokeWidth="5" className={softStroke} />
      <circle cx="94" cy="238" r="7" className="fill-teal-500" />
      <circle cx="382" cy="108" r="6" className="fill-sky-500" />
    </>
  );
}

function DengueArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <ellipse cx="238" cy="176" rx="24" ry="52" className={surfaceFill} />
        <path d="M238 124v-28M238 228v30M221 143l-42-34M255 143l42-34M218 169l-62-10M258 169l62-10M219 197l-52 37M257 197l52 37" />
        <path d="M219 151c-45-37-79-18-60 15 15 25 43 23 64 9M257 151c45-37 79-18 60 15-15 25-43 23-64 9" />
        <path d="M229 126c-15-17-10-31 9-31s24 14 9 31" />
      </g>
      <g fill="none" strokeLinecap="round" strokeWidth="5" className={softStroke}>
        <path d="M104 270c16-22 34-22 51 0s35 22 52 0" />
        <path d="M297 92h39M316 73v38" />
      </g>
    </>
  );
}

function FluArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <circle cx="224" cy="130" r="46" className={surfaceFill} />
        <path d="M182 125c8-42 30-61 67-43 18 9 27 25 29 47-15-4-29-14-38-29-15 17-34 26-58 25Z" className="fill-slate-800 dark:fill-slate-100" />
        <path d="M206 143c6 5 12 5 18 0M241 143c6 5 12 5 18 0M223 161c8 5 16 5 24 0" />
        <path d="M178 197c-37 14-58 48-61 101M270 197c37 14 58 48 61 101M171 298h106" />
        <path d="M185 199l-20 39 45 28 23-39-48-28ZM263 199l20 39-45 28-23-39 48-28Z" className={surfaceFill} />
      </g>
      <g fill="none" strokeLinecap="round" strokeWidth="5" className={softStroke}>
        <path d="M350 112v58M335 170h30M344 112a7 7 0 0 1 14 0v37a18 18 0 1 1-14 0v-37Z" />
        <path d="M328 215l19-10M333 238h23M328 262l19 10" />
      </g>
    </>
  );
}

function HandFootMouthArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M180 275c-20-28-26-58-17-87l11-43c3-11 18-9 17 3l-4 31 9-63c2-12 19-11 18 2l-3 56 10-70c2-12 19-10 18 3l-4 68 12-58c3-12 20-8 17 5l-8 63 9-31c4-12 21-6 17 7l-18 71c-7 26-27 42-54 40h-30Z" className={surfaceFill} />
        <path d="M92 126c19-20 47-20 66 0 18 19 18 48 0 66-19 20-47 20-66 0-18-18-18-47 0-66Z" className={surfaceFill} />
        <path d="M103 158c14 9 28 9 42 0M318 126c17 10 30 25 37 45l12 36c7 21-6 42-27 46l-50 10c-13 3-19-16-6-21l28-11-34 3" className={surfaceFill} />
      </g>
      <g className="fill-teal-500">
        <circle cx="201" cy="218" r="7" /><circle cx="229" cy="239" r="6" /><circle cx="251" cy="205" r="7" />
        <circle cx="116" cy="146" r="5" /><circle cx="137" cy="171" r="6" /><circle cx="337" cy="209" r="6" />
      </g>
    </>
  );
}

function HypertensionArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M92 211c39-32 85-40 137-24l52 16-18 69-55-13c-42-10-79-4-112 18" className={surfaceFill} />
        <rect x="173" y="173" width="92" height="96" rx="16" className="fill-teal-50 dark:fill-teal-950" />
        <path d="M265 225c43 0 49-55 45-88" />
        <circle cx="310" cy="116" r="55" className={surfaceFill} />
        <path d="M310 116l28-24M310 76v11M270 116h11M339 116h11" />
      </g>
      <path d="M337 215c-22-26-56 3-25 34l25 23 25-23c31-31-3-60-25-34Z" fill="none" strokeLinejoin="round" strokeWidth="5" className={softStroke} />
      <path d="M324 246h11l7-13 9 24 7-11h14" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" className={softStroke} />
    </>
  );
}

function DiabetesArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <rect x="108" y="80" width="176" height="210" rx="28" className={surfaceFill} />
        <rect x="136" y="113" width="120" height="78" rx="12" />
        <path d="M153 164h19l11-25 18 42 14-27h24" />
        <circle cx="196" cy="235" r="22" />
        <path d="M196 257v38M178 290h36" />
        <path d="M330 98c-19 29-41 53-41 82 0 25 19 44 41 44s41-19 41-44c0-29-22-53-41-82Z" className="fill-teal-50 dark:fill-teal-950" />
      </g>
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={softStroke}>
        <path d="M308 264l22-13 22 13v26l-22 13-22-13Z" />
        <path d="M330 251v-18M308 277l-18 10M352 277l18 10" />
      </g>
    </>
  );
}

function MalariaArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeWidth="5" className={commonStroke}>
        <circle cx="170" cy="132" r="53" className={surfaceFill} />
        <circle cx="304" cy="151" r="61" className={surfaceFill} />
        <circle cx="214" cy="251" r="48" className={surfaceFill} />
        <circle cx="170" cy="132" r="26" className={softStroke} />
        <path d="M285 139c13-21 42-18 50 4 8 22-11 44-34 38-20-5-27-27-16-42Z" className={softStroke} />
        <path d="M194 251c13-20 31-23 43-8 12 15 3 35-16 35-18 0-29-13-27-27Z" className={softStroke} />
      </g>
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" className={softStroke}>
        <path d="M93 218c20-36 40-41 62-16M343 244c18-28 35-30 52-6" />
        <path d="M349 85c13 18 16 39 9 63M365 102l22-13M361 125l27 4" />
      </g>
      <circle cx="170" cy="132" r="7" className="fill-teal-500" />
      <circle cx="315" cy="159" r="6" className="fill-sky-500" />
    </>
  );
}

function TuberculosisArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <rect x="104" y="56" width="268" height="250" rx="24" className="fill-white stroke-slate-800 dark:fill-slate-900 dark:stroke-slate-100" strokeWidth="5" />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M238 91v72M238 135l-31 28M238 135l31 28" />
        <path d="M205 137c-42 5-73 44-73 93 0 29 15 48 41 48 32 0 54-29 54-70v-45c-6-17-13-26-22-26Z" className="fill-teal-50 dark:fill-teal-950" />
        <path d="M271 137c42 5 73 44 73 93 0 29-15 48-41 48-32 0-54-29-54-70v-45c6-17 13-26 22-26Z" className="fill-teal-50 dark:fill-teal-950" />
      </g>
      <g className="fill-teal-500">
        <circle cx="178" cy="178" r="9" /><circle cx="198" cy="201" r="6" /><circle cx="300" cy="186" r="8" />
      </g>
      <g fill="none" strokeLinecap="round" strokeWidth="4" className={softStroke}>
        <path d="M118 87l21 8M111 110l24 3M337 84l20-9M342 108l25-4" />
      </g>
    </>
  );
}

function HepatitisArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M96 174c22-64 77-102 145-102 70 0 124 32 150 87-31 10-55 26-72 49-18 25-47 42-82 42h-80c-46 0-76-34-61-76Z" className={surfaceFill} />
        <path d="M242 74c-13 50-3 99 30 145M178 250c8-30 6-55-6-75" />
      </g>
      <g fill="none" strokeWidth="5" className={softStroke}>
        <circle cx="329" cy="224" r="48" className="fill-teal-50 dark:fill-teal-950" />
        <circle cx="329" cy="224" r="27" />
        <path d="M329 176v-16M329 288v-16M281 224h-16M393 224h-16M295 190l-11-11M374 269l-11-11M363 190l11-11M284 269l11-11" />
      </g>
      <text x="329" y="236" textAnchor="middle" className="fill-teal-700 text-3xl font-bold dark:fill-teal-300">B</text>
    </>
  );
}

function StrokeArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <circle cx="210" cy="132" r="57" className={surfaceFill} />
        <path d="M176 129c10-8 20-8 30 0M222 129c10-8 20-8 30 0M188 161c19 13 38 10 56-8" />
        <path d="M127 298c5-70 35-108 83-108 34 0 60 19 73 55M161 217l-47 52M259 221l71 16" />
        <path d="M330 237l35 10M365 247l-15 35" />
      </g>
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={softStroke}>
        <circle cx="350" cy="116" r="47" className="fill-teal-50 dark:fill-teal-950" />
        <path d="M350 85v33l22 14" />
        <path d="M323 165l15-22 12 10 14-25" />
      </g>
    </>
  );
}

function AsthmaArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <circle cx="207" cy="170" r="86" className={surfaceFill} />
        <path d="M207 103v54M207 132l-37 35M207 132l37 35M170 167l-16 34M244 167l16 34" />
        <path d="M154 201c23 3 40 14 53 33M260 201c-23 3-40 14-53 33" />
        <path d="M315 107h48v131h-48zM326 83h26v24M327 238l-10 48h44l-10-48" className={surfaceFill} />
      </g>
      <g fill="none" strokeLinecap="round" strokeWidth="5" className={softStroke}>
        <path d="M160 168h20M234 168h20" />
        <path d="M306 145c-27 0-39 12-45 35M302 164c-18 2-27 10-32 24" />
      </g>
    </>
  );
}

function CopdArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M235 97v65M235 137l-31 29M235 137l31 29" />
        <path d="M202 143c-48 12-79 57-74 108 3 30 23 45 49 36 35-12 46-45 46-91v-35c-5-13-12-19-21-18Z" className={surfaceFill} />
        <path d="M268 143c48 12 79 57 74 108-3 30-23 45-49 36-35-12-46-45-46-91v-35c5-13 12-19 21-18Z" className={surfaceFill} />
      </g>
      <g fill="none" strokeWidth="4" className={softStroke}>
        <circle cx="169" cy="210" r="18" /><circle cx="194" cy="239" r="24" /><circle cx="293" cy="211" r="25" /><circle cx="316" cy="246" r="17" />
        <path d="M76 126c29-13 52-5 69 24M72 153c21-8 38-2 51 16" strokeLinecap="round" />
      </g>
      <g className="fill-slate-500 dark:fill-slate-400">
        <circle cx="86" cy="104" r="7" /><circle cx="110" cy="111" r="5" /><circle cx="129" cy="127" r="6" />
      </g>
    </>
  );
}

function DiarrheaArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M127 104c-26 26-28 68-8 95 14 18 16 42 6 65-11 25 4 52 31 52h157c27 0 43-28 31-52-10-23-8-47 6-65 20-27 18-69-8-95" className={surfaceFill} />
        <path d="M165 137c-26 0-31 38-6 45 24 7 26 39 2 48-25 9-20 47 7 47h19M305 137c26 0 31 38 6 45-24 7-26 39-2 48 25 9 20 47-7 47h-19" />
        <path d="M190 137h90v140h-90c-22 0-28-31-7-39 21-8 21-39 0-47-21-8-15-54 7-54Z" />
      </g>
      <path d="M367 189c-16 23-31 42-31 61 0 20 14 34 31 34s31-14 31-34c0-19-15-38-31-61Z" fill="none" strokeLinejoin="round" strokeWidth="5" className={softStroke} />
    </>
  );
}

function MeaslesArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <circle cx="225" cy="112" r="49" className={surfaceFill} />
        <path d="M177 107c6-38 28-57 65-48 24 6 37 25 38 53-20-3-36-12-48-28-13 14-31 22-55 23Z" className="fill-slate-800 dark:fill-slate-100" />
        <path d="M162 298c2-77 24-118 63-118s61 41 63 118M177 219l-49 40M273 219l49 40" />
      </g>
      <g className="fill-teal-500">
        <circle cx="201" cy="123" r="5" /><circle cx="237" cy="136" r="5" /><circle cx="210" cy="209" r="6" /><circle cx="244" cy="227" r="7" /><circle cx="198" cy="252" r="5" /><circle cx="256" cy="273" r="6" />
      </g>
      <g fill="none" strokeWidth="5" className={softStroke}>
        <circle cx="350" cy="151" r="43" className="fill-teal-50 dark:fill-teal-950" />
        <circle cx="337" cy="146" r="5" className="fill-teal-500" /><circle cx="359" cy="158" r="6" className="fill-teal-500" />
      </g>
    </>
  );
}

function RabiesArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M110 122l31-42 24 36c22-10 48-10 70 0l24-36 31 42c24 24 28 63 9 92-20 30-56 48-99 48s-79-18-99-48c-19-29-15-68 9-92Z" className={surfaceFill} />
        <circle cx="158" cy="157" r="7" className="fill-slate-800 dark:fill-slate-100" /><circle cx="242" cy="157" r="7" className="fill-slate-800 dark:fill-slate-100" />
        <path d="M175 201c16 13 34 13 50 0M200 176l-11 12h22Z" />
        <path d="M92 285h215c26 0 50 9 69 26M126 261l20 24" />
      </g>
      <g fill="none" strokeLinecap="round" strokeWidth="5" className={softStroke}>
        <path d="M313 164c18 22 25 46 21 72" />
        <path d="M323 183c15 8 27 8 38 0M334 205c12 7 22 7 31 0" />
        <path d="M157 278l12-12M177 285l13-13" />
      </g>
    </>
  );
}

function FoodPoisoningArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M94 250h268M117 238c0-66 53-119 119-119s119 53 119 119H117Z" className={surfaceFill} />
        <path d="M221 119c0-19 30-19 30 0M153 273h166" />
        <path d="M165 189c18-13 36-13 54 0 17 12 34 12 51 0 18-13 36-13 54 0" />
      </g>
      <g fill="none" strokeLinecap="round" strokeWidth="5" className={softStroke}>
        <circle cx="348" cy="111" r="42" className="fill-teal-50 dark:fill-teal-950" />
        <path d="M348 82v12M348 128v12M319 111h12M365 111h12M328 91l9 9M359 122l9 9M368 91l-9 9M337 122l-9 9" />
      </g>
      <circle cx="348" cy="111" r="8" className="fill-teal-500" />
    </>
  );
}

function DepressionArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <circle cx="200" cy="108" r="42" className={surfaceFill} />
        <path d="M158 106c4-34 22-51 54-47 25 3 40 20 43 51-19-2-34-11-44-26-14 14-32 21-53 22Z" className="fill-slate-800 dark:fill-slate-100" />
        <path d="M132 296c3-74 26-115 68-115 43 0 67 41 69 115M159 220l41 40 41-40M200 260v36" />
        <path d="M277 250c28-31 63-41 105-29M288 278c29-20 61-24 96-13" />
      </g>
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={softStroke}>
        <path d="M299 84h87a24 24 0 0 1 24 24v36a24 24 0 0 1-24 24h-38l-28 24 5-24h-26a24 24 0 0 1-24-24v-36a24 24 0 0 1 24-24Z" className="fill-teal-50 dark:fill-teal-950" />
        <path d="M302 125h19M333 125h19M364 125h19" />
      </g>
    </>
  );
}

function GeneralArtwork() {
  return (
    <>
      <ArtworkBackdrop />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" className={commonStroke}>
        <path d="M154 104h166a20 20 0 0 1 20 20v143a20 20 0 0 1-20 20H154a20 20 0 0 1-20-20V124a20 20 0 0 1 20-20Z" className={surfaceFill} />
        <path d="M199 104V87h76v17M186 153h103M186 241h103M184 200h31l12-29 21 57 15-39 12 18h26" />
      </g>
    </>
  );
}

function ArtworkBody({ kind }: { kind: ArtworkKind }) {
  switch (kind) {
    case "dengue": return <DengueArtwork />;
    case "flu": return <FluArtwork />;
    case "hand-foot-mouth": return <HandFootMouthArtwork />;
    case "hypertension": return <HypertensionArtwork />;
    case "diabetes": return <DiabetesArtwork />;
    case "malaria": return <MalariaArtwork />;
    case "tuberculosis": return <TuberculosisArtwork />;
    case "hepatitis": return <HepatitisArtwork />;
    case "stroke": return <StrokeArtwork />;
    case "asthma": return <AsthmaArtwork />;
    case "copd": return <CopdArtwork />;
    case "diarrhea": return <DiarrheaArtwork />;
    case "measles": return <MeaslesArtwork />;
    case "rabies": return <RabiesArtwork />;
    case "food-poisoning": return <FoodPoisoningArtwork />;
    case "depression": return <DepressionArtwork />;
    default: return <GeneralArtwork />;
  }
}

export function HealthTopicArtwork({
  slug,
  name,
  compact = false,
  decorative = false,
  className,
}: HealthTopicArtworkProps) {
  const kind = artworkKindForTopic(slug, name);

  return (
    <svg
      viewBox="0 0 480 360"
      role={decorative ? undefined : "img"}
      aria-hidden={decorative || undefined}
      aria-label={decorative ? undefined : `Minh họa chủ đề ${name}`}
      focusable="false"
      data-artwork-kind={kind}
      className={cn("h-auto w-full", compact && "max-h-48", className)}
    >
      <ArtworkBody kind={kind} />
    </svg>
  );
}
