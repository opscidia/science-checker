import { useNavigate, useSearchParams } from "react-router-dom";
import "./SearchPage.scss";
import logo from "../../assets/images/logo.png";
import { useEffect, useState } from "react";
import { FiSearch } from "react-icons/fi";
import { FaArrowRightLong } from "react-icons/fa6";
import axios from "axios";
import Article from "../../components/Article/Article";
import ArticlePopup from "../../popups/ArticlePopup/ArticlePopup";
import ArticlesPopup from "../../popups/ArticlesPopup/ArticlesPopup";
import { ToastContainer } from "react-toastify";
import { toast } from "react-toastify";
import CitationsPopup from "../../popups/CitationsPopup/CitationsPopup";

function SearchPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [keywords, setKeywords] = useState("");
  const [articleResults, setArticleResults] = useState([]);
  const [showArticlePopup, setShowArticlePopup] = useState(false);
  const [showArticlesPopup, setShowArticlesPopup] = useState(false);
  const [showCitationsPopup, setShowCitationsPopup] = useState(false);
  const [articleData, setArticleData] = useState({});
  const [selectedArticles, setSelectedArticles] = useState([]);
  const [articleCitation, setArticleCitation] = useState({});

  const handleChange = (articleId) => {
    return (e) => {
      if (e.target.checked) {
        if (selectedArticles.length >= 5) {
          toast.error("You can't select more than 5 articles");
          return;
        }
        const newSelectedArticles = selectedArticles.concat(articleId);
        setSelectedArticles(newSelectedArticles);
      } else {
        const newSelectedArticles = selectedArticles.filter(
          (id) => id !== articleId
        );
        setSelectedArticles(newSelectedArticles);
      }
    };
  };

  useEffect(() => {
    const query = searchParams.get("query");
    if (query) {
      setKeywords(query);
      setSelectedArticles([]);

      const fetchArticles = async () => {
        try {
          const response = await axios.get(`/api/search?query=${query}`);
          setArticleResults(response?.data?.hits);
        } catch (error) {
          console.error(error);
        }
      };
      fetchArticles();
    }
  }, [searchParams]);

  const handleChangeKeywords = (event) => {
    setKeywords(event.target.value);
  };

  const handleClickSearch = () => {
    navigate(`/search?query=${keywords}`);
  };

  const handleKeyPress = (event) => {
    if (event.key === "Enter") {
      handleClickSearch();
    }
  };

  const handleArticleClick = async (id) => {
    const { data } = await axios.get(`/api/article/${id}`);
    setShowArticlePopup(true);
    setArticleData(data);
  };

  const handleCloseCitationsPopup = () => {
    setShowCitationsPopup(false);
    setArticleCitation({});
  }

  const handleInerrogateArticles = () => {
    if (selectedArticles.length === 0) {
      toast.error("You must select at least one article");
    }
    else if (selectedArticles.length === 1) {
      handleArticleClick(selectedArticles[0]);
    }
    else setShowArticlesPopup(true);
  }

  return (
    <div className="searchpage pt-4">
      <div className="searchpage__container">
        <img
          className="searchpage__logo"
          width={210}
          src={logo}
          alt="Logo Opscidia"
        />
        <div className="searchpage__input__container position-relative my-4 m-3 ms-4">
          <input
            className="searchpage__input px-5"
            placeholder="Ask a question"
            type="text"
            value={keywords}
            onChange={handleChangeKeywords}
            onKeyPress={handleKeyPress}
          />
          <FiSearch
            onClick={handleClickSearch}
            className="c-pointer position-absolute top-50 end-0 translate-middle-y me-4"
            color="#1B1B42"
            size="1.6em"
          />
        </div>
      </div>
      <div className="searchpage__results">
        <div
          className="searchpage__interrogate__container mb-2"
        >
          <span
            className="searchpage__interrogate ms-4 c-pointer d-flex align-items-center w-fit-content"
            onClick={handleInerrogateArticles}
          >
            <span className="ms-2 me-1 py-1">
              <strong>?</strong> Ask a question using {selectedArticles.length} {selectedArticles.length !== 1 ? "papers" : "paper"}
            </span>
            <span className="searchpage__interrogate__icon py-1">
              <FaArrowRightLong
                className="mx-3"
              />
            </span>

          </span>
        </div>
        {articleResults.map((article) => (
          <Article
            key={article.id}
            onClick={() => handleArticleClick(article.id)}
            {...{
              ...article,
              selectedArticles,
              handleChange,
              setShowCitationsPopup,
              setArticleCitation
            }}
            type="search"
          />
        ))}
      </div>
      <ArticlePopup
        {...{
          showArticlePopup,
          setShowArticlePopup,
          articleData,
        }}
      />
      <ArticlesPopup
        {...{
          showArticlesPopup,
          setShowArticlesPopup,
          selectedArticles,
          setShowCitationsPopup,
          setArticleCitation
        }}
      />
      <CitationsPopup
        showPopup={showCitationsPopup}
        handleClosePopup={handleCloseCitationsPopup}
        {...articleCitation}
      />
      <ToastContainer />
    </div>
  );
}

export default SearchPage;
