import "./SearchContainer.scss";
import { useState } from "react";
import { FiSearch } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

function SearchContainer() {
  const navigate = useNavigate();
  const [keywords, setKeywords] = useState("");

  const handleItemClick = (item) => {
    setKeywords(item);
  };

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

  return (
    <div className="search__container py-5 px-3">
      <h3 className="search__container__title">
        Your AI solution for instant scientific answers
      </h3>
      <h4 className="search__container__subtitle mt-3">
        Let AI scour scientific documents to find your answers.
      </h4>

      <div className="search__container__input__container position-relative my-4 m-3 ms-4">
        <input
          className="search__container__input px-5"
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
      <div className="search__container__suggestions c-pointer">
        {suggestions.map((suggestion, index) => (
          <div
            key={index}
            className="search__container__suggestions__item"
            onClick={() => handleItemClick(suggestion)}
          >
            {suggestion}
          </div>
        ))}
      </div>
    </div>
  );
}

const suggestions = [
  "Does ARN vaccines have an impact on childhood autism ?",
  "Does artificial intelligence impact the field of law ?",
  "What are the impacts of air pollution on human health ?",
  "What are microplastics ?",
  "What are the impacts of Covid-19 in india ?",
];

export default SearchContainer;
