import type { Role } from "@/lib/rbac";

export interface SessionUser {
  id: string;
  full_name: string;
  email: string;
  role: Role;
}

export interface SessionTenant {
  id: string;
  name: string;
  slug: string;
  sector: string;
}

export interface Me {
  user: SessionUser;
  tenant: SessionTenant;
}
