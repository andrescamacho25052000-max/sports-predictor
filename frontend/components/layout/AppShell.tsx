import TopBar from "./TopBar";
import Sidebar from "./Sidebar";
import BottomNav from "./BottomNav";

/**
 * Shell global del layout Statix: barra superior fija, sidebar (desktop),
 * navegación inferior (mobile) y el área de contenido de cada página.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopBar />
      <Sidebar />
      <div className="pt-16 lg:pl-64">
        <main className="min-h-[calc(100vh-4rem)] pb-24 lg:pb-10">{children}</main>
      </div>
      <BottomNav />
    </div>
  );
}
