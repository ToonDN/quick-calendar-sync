import { GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET } from "$env/static/private";
import type { PageServerLoad } from "./$types";
import jwt from "jsonwebtoken";
import fs from "fs";

export const load: PageServerLoad = async (event) => {
    if (
        event.url.searchParams.has("code") &&
        event.url.searchParams.has("scope") &&
        event.url.searchParams.has("authuser") &&
        event.url.searchParams.has("prompt")
    ) {
        const body = {
            code: event.url.searchParams.get("code")!,
            client_secret: GOOGLE_CLIENT_SECRET,
            client_id: GOOGLE_CLIENT_ID,
            grant_type: "authorization_code",
            redirect_uri: "http://localhost:5173/",
        };

        const response = await fetch("https://oauth2.googleapis.com/token", {
            method: "POST",
            body: JSON.stringify(body),
            headers: {
                "content-type": "application/json",
            },
        });

        if (response.status === 200) {
            const responseData = await response.json();
            const refreshToken = responseData.refresh_token;

            if (refreshToken) {
                // rome-ignore lint/suspicious/noExplicitAny: <explanation>
                const jwtData = jwt.decode(responseData.id_token) as jwt.JwtPayload;
                fs.writeFileSync(
                    `../tokens/${jwtData.email}.json`,
                    JSON.stringify({
                        token: responseData,
                        jwtData: jwtData,
                        
                    }),
                )
            } else {
                console.log("No refresh token in response", responseData);
            }
        } else {
            console.log("Request failed", response.status);
            const responseData = await response.json();
            console.log(responseData);
        }
    }
};