import { useState, useEffect } from "react";
import { AuthorityView } from "./components/AuthorityView";
import { PublicView } from "./components/PublicView";

function App() {
  const [currentPath, setCurrentPath] = useState<string>(() => window.location.pathname);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = (path: string) => {
    if (path !== window.location.pathname) {
      window.history.pushState(null, "", path);
      setCurrentPath(path);
    }
  };

  if (currentPath === "/public") {
    return <PublicView onNavigate={navigate} />;
  }

  return <AuthorityView onNavigate={navigate} />;
}

export default App;
