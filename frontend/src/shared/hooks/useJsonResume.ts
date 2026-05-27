export interface JsonResume {
  basics?: {
    name?: string;
    label?: string;
    email?: string;
    phone?: string;
    url?: string;
    summary?: string;
    location?: { city?: string; countryCode?: string };
    profiles?: Array<{ network?: string; url?: string; username?: string }>;
  };
  work?: Array<{
    name?: string;
    position?: string;
    role?: string;
    url?: string;
    startDate?: string;
    endDate?: string;
    summary?: string;
    highlights?: string[];
    company?: string;
  }>;
  education?: Array<{
    institution?: string;
    area?: string;
    studyType?: string;
    degree?: string;
    startDate?: string;
    endDate?: string;
  }>;
  skills?: Array<{ name?: string; keywords?: string[] }>;
  projects?: Array<{
    name?: string;
    description?: string;
    url?: string;
    startDate?: string;
    endDate?: string;
    highlights?: string[];
  }>;
  languages?: Array<{ language?: string; fluency?: string }>;
  certifications?: Array<{ name?: string; issuer?: string; date?: string }>;
}

export function useJsonResume(doc: { content_json?: unknown } | null) {
  const resume = (doc?.content_json ?? null) as JsonResume | null;
  return {
    resume,
    basics: resume?.basics ?? {},
    work: resume?.work ?? [],
    education: resume?.education ?? [],
    skills: resume?.skills ?? [],
    projects: resume?.projects ?? [],
    languages: resume?.languages ?? [],
    certifications: resume?.certifications ?? [],
  };
}
