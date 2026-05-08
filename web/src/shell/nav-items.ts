export type NavItem = {
  path: string;
  labelKey: string;
  roles: string[];
};

export const NAV_ITEMS: NavItem[] = [
  { path: "/dashboard", labelKey: "dashboard", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/tenants", labelKey: "tenantSwitch", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/users", labelKey: "users", roles: ["org_admin", "system_admin"] },
  { path: "/courses", labelKey: "courses", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/lessons", labelKey: "lessons", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/tests", labelKey: "tests", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/assignments", labelKey: "assignments", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/homework-reviews", labelKey: "homeworkReviews", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/analytics", labelKey: "analytics", roles: ["org_admin", "teacher", "system_admin"] },
  { path: "/settings", labelKey: "settings", roles: ["org_admin", "teacher", "system_admin"] },
];
