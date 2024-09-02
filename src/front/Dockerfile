FROM node:18-alpine
LABEL maintainer "wahid.hibot@opscidia.com"

# Set working directory
WORKDIR /usr/src/front

ENV PATH /app/node_modules/.bin:$PATH

# Copy package.json and package-lock.json to install dependencies
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the React app
RUN npm run build

# Install `serve` globally to serve the production build
RUN npm install -g serve

# Expose port 3000
EXPOSE 3000

# Command to serve the built React app using `serve`
CMD ["serve", "-s", "dist", "-l", "3000"]