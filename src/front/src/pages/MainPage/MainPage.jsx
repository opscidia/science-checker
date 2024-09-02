import "./MainPage.scss";
import SearchContainer from "../../components/SearchContainer/SearchContainer";
import logo from "../../assets/images/logo.png";

function MainPage() {
  return (
    <div className="mainpage d-flex flex-column align-items-center">
      <h1 className="mainpage__title mb-5">Science Checker</h1>
      <SearchContainer />
      <div className="mainpage__footer mt-5">
        By
        <img
          className="mainpage__footer__logo"
          src={logo}
          alt="Logo Opscidia"
        />
      </div>
    </div>
  );
}

export default MainPage;
