document.addEventListener("DOMContentLoaded", async () => {

    // ==== Fetch User Info ====
    const res = await fetch("/api/user-info");
    if (!res.ok) return;
    const user = await res.json();

    // Name & Membership
    document.querySelector("header h2 span").textContent = user.name;
    document.querySelector("nav .md\\:block p:nth-child(2)").textContent = user.membership;
    document.querySelector("nav .size-10").style.backgroundImage = `url(${user.profilePic})`;

    // Readiness & Stats
    document.querySelector(".flex-grow .absolute span.text-3xl").textContent = `${user.readiness}%`;
    const stats = document.querySelectorAll(".grid div");
    stats[0].querySelector("p").textContent = user.sessionsCompleted;
    stats[1].querySelector("p").textContent = user.improvementRate;

    // Populate Skills
    const skillContainer = document.querySelector(".snap-center .flex-1");
    skillContainer.innerHTML = "";
    user.skills.forEach(skill => addSkillToDOM(skill));

    // Add Skill button
    document.querySelector(".snap-center button").addEventListener("click", async () => {
        const name = prompt("Skill name?");
        if (!name) return;
        const percent = parseInt(prompt("Skill proficiency % (0-100)"));
        if (isNaN(percent)) return;
        await fetch("/api/add-skill", {
            method: "POST",
            body: new URLSearchParams({ user_id: 1, name, percent })
        });
        addSkillToDOM({ name, percent, color: "primary", note: "Newly added skill" });
    });

    function addSkillToDOM(skill) {
        const div = document.createElement("div");
        div.innerHTML = `
        <div class="flex justify-between mb-2">
            <span class="text-sm font-semibold text-dark">${skill.name}</span>
            <span class="text-sm font-bold text-${skill.color}">${skill.percent}%</span>
        </div>
        <div class="h-2 w-full bg-white rounded-full overflow-hidden">
            <div class="h-full bg-${skill.color} w-[${skill.percent}%] rounded-full shadow-[0_0_10px_rgba(232,60,145,0.5)]"></div>
        </div>
        <p class="text-xs text-dark/50 mt-1">${skill.note}</p>`;
        skillContainer.appendChild(div);
    }

    // Navigation links
    const navLinks = document.querySelectorAll("nav a");
    if(navLinks.length >= 4){
        navLinks[0].href = "ai.html";
        navLinks[1].href = "edit-profile.html";
        navLinks[2].href = "analytics.html";
        navLinks[3].href = "log-out.html";
    }

    // AI Chat (ai.html)
    const aiBtn = document.getElementById("sendAI");
    if(aiBtn){
        aiBtn.addEventListener("click", async () => {
            const input = document.getElementById("userInput").value;
            const res = await fetch("/api/ai-response", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: input, user_id: 1 })
            });
            const data = await res.json();
            document.getElementById("aiResponse").innerText = data.response || "Error";
        });
    }

    // Analytics page
    if(document.getElementById("totalUsers")){
        const res = await fetch("/api/analytics-data");
        const data = await res.json();
        document.getElementById("totalUsers").textContent = data.total_users;
        document.getElementById("queriesToday").textContent = data.queries_today;
        document.getElementById("totalQueries").textContent = data.total_queries;
    }

});
