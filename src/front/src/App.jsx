import "./App.scss";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import MainPage from "./pages/MainPage/MainPage";
import SearchPage from "./pages/SearchPage/SearchPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="" element={<MainPage />} />
        <Route path="search" element={<SearchPage />} />
      </Routes>
    </Router>
  );
}

export default App;
