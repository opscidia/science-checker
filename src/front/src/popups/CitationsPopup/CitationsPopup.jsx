import { Accordion } from "react-bootstrap";
import CommonPopup from "../../components/CommonPopup/CommonPopup";
import "./CitationsPopup.scss";
import { PropTypes } from "prop-types";


CitationsPopup.propTypes = {
  showPopup: PropTypes.bool,
  handleClosePopup: PropTypes.func,
  bibCitation: PropTypes.string,
  apaCitation: PropTypes.string,
  mlaCitation: PropTypes.string,
  isoCiation: PropTypes.string,
};


function CitationsPopup({
  showPopup,
  handleClosePopup,
  bibCitation,
  apaCitation,
  mlaCitation,
  isoCiation,
}) {
  const citationsList = ["Bibtex", "APA", "MLA", "ISO 690"];

  return (
    <CommonPopup
      title="Citations"
      showPopup={showPopup}
      closePopup={handleClosePopup}
      type="2"
    >
      <Accordion
        className="accordion-class w-75 mx-auto my-3"
        defaultActiveKey={0}
      >
        {citationsList.map((citationItem, index) => {
          return (
            <Accordion.Item className="mb-3" eventKey={index} key={index}>
              <Accordion.Header>{citationItem}</Accordion.Header>
              <Accordion.Body className="pt-1">
                <div className="citation-text text-start mt-2">
                  {citationItem === "Bibtex" && <pre>{bibCitation}</pre>}
                  {citationItem === "APA" && apaCitation}
                  {citationItem === "MLA" && mlaCitation}
                  {citationItem === "ISO 690" && isoCiation}
                </div>
              </Accordion.Body>
            </Accordion.Item>
          );
        })}
      </Accordion>
    </CommonPopup>
  );
}

export default CitationsPopup;
