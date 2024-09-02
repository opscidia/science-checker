export function filterTextKeywordsByTag(
    text,
    openTag = "<span class='hglt'>",
    closeTag = "</span>"
) {
    let keywords = [];

    if (typeof text === "string")
        return filterTextTitleByTag(text, openTag, closeTag);

    text.forEach((i) => {
        let myFirstIndex = i.indexOf(openTag);
        let myLastIndex = i.indexOf(closeTag);

        while (myFirstIndex !== -1) {
            keywords.push(i.slice(myFirstIndex + openTag.length, myLastIndex));
            myFirstIndex = i.indexOf(openTag, myFirstIndex + 1);
            myLastIndex = i.indexOf(closeTag, myLastIndex + 1);
        }
    });
    return [...new Set(keywords)];
}


export function filterTextTitleByTag(
    text,
    openTag = "<span class='hglt'>",
    closeTag = "</span>"
) {
    let keywords = [];

    let myFirstIndex = text.indexOf(openTag);
    let myLastIndex = text.indexOf(closeTag);
    while (myFirstIndex !== -1) {
        keywords.push(text.slice(myFirstIndex + openTag.length, myLastIndex));
        myFirstIndex = text.indexOf(openTag, myFirstIndex + 1);
        myLastIndex = text.indexOf(closeTag, myLastIndex + 1);
    }

    return [...new Set(keywords)];
}


export const renderCitations = (citation) => {
    if (isNaN(citation) || citation === -1) return "Number of citations unknown";
    else return `${citation} Citations`;
};

export const isArray = (value) => {
    return value && typeof value === "object" && value.constructor === Array;
}

export const isObject = (value) => {
    return value && typeof value === "object" && value.constructor === Object;
}

export function completeHTML(htmlString) {
    const unclosedTags = htmlString.match(/<span[^>]*>/g) || [];
    const closedTags = htmlString.match(/<\/span>/g) || [];

    const unclosedTagCount = unclosedTags.length - closedTags.length;
    if (unclosedTagCount === 0) {
        return htmlString; // All tags are closed
    }

    const closingTags = "</span>".repeat(unclosedTagCount);
    return htmlString + closingTags;
}


export const saveToLocalStorage = (name, data) => {
    localStorage.setItem(name, JSON.stringify(data));
};

export const getFromLocalStorage = (name) => {
    return JSON.parse(localStorage.getItem(name));
};
