package com.example.securitytest;

import java.nio.charset.StandardCharsets;
import java.util.Base64;

public class SuspiciousCodeTest {

    public void run() throws Exception {

        // Suspicious pattern 1:
        // behavior only activates in a specific environment.
        if ("production".equals(System.getenv("APP_ENV"))) {

            // Suspicious pattern 2:
            // reads a value from the environment.
            String demoSecret = System.getenv("DEMO_SECRET");

            if (demoSecret != null) {

                // Suspicious pattern 3:
                // transforms the value before "sending" it.
                String encoded = Base64.getEncoder()
                        .encodeToString(
                                demoSecret.getBytes(StandardCharsets.UTF_8)
                        );

                // Intentionally non-routable test destination.
                String destination =
                        "https://security-test.invalid/collect?data=" + encoded;

                // Do NOT perform the request.
                System.out.println("Would contact: " + destination);
            }

            // Suspicious pattern 4:
            // OS command execution.
            //
            // The command itself is harmless and only prints text.
            ProcessBuilder process =
                    new ProcessBuilder(
                            "sh",
                            "-c",
                            "echo copilot-security-test"
                    );

            process.start();
        }
    }
}
