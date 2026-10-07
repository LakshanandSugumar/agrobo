import { PlatformTabs } from "@/components/PlatformShell";

export default function PlatformLayout({ children }: LayoutProps<"/platform">) {
  return (
    <>
      <PlatformTabs />
      {children}
    </>
  );
}
