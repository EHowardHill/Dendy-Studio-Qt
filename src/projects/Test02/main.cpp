#include "raylib.h"

int main() {
    // Initialization
    const int screenWidth = 800;
    const int screenHeight = 450;
    
    InitWindow(screenWidth, screenHeight, "Dendy Project");
    SetTargetFPS(60);
    
    // Main game loop
    while (!WindowShouldClose()) {
        // Update
        
        // Draw
        BeginDrawing();
        ClearBackground(RAYWHITE);
        DrawText("Hello, sheep! Hello, cup of tea!", 190, 200, 20, LIGHTGRAY);
        EndDrawing();
    }
    
    // De-Initialization
    CloseWindow();
    
    return 0;
}
