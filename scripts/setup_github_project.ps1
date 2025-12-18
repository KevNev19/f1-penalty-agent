# F1 Agent Project Setup Script
# Run this to setup the GitHub Project and link Roadmap issues.

Write-Host "Checking GitHub Auth..."
# Ensure we have project scope
gh auth refresh -s project, read:org

# Get current user/repo context
$repoInfo = gh repo view --json owner, name -q ".owner.login + '/' + .name"
$owner = gh repo view --json owner -q ".owner.login"
Write-Host "Target: $repoInfo ($owner)"

# Create Project
Write-Host "Creating Project 'F1 Agent Production Roadmap'..."
$project = gh project create --owner $owner --title "F1 Agent Production Roadmap" --format json | ConvertFrom-Json
$projectId = $project.number
Write-Host "Project Created: #$projectId ($($project.url))"

# List of Issue IDs created for roadmap (17, 18, 19, 20, 21)
# Fetch them dynamically if needed, but we know them.
$issueIds = @(17, 18, 19, 20, 21)

Write-Host "Adding Issues to Project..."
foreach ($id in $issueIds) {
    $issueUrl = "https://github.com/$repoInfo/issues/$id"
    gh project item-create $projectId --owner $owner --url $issueUrl
    Write-Host "Added Issue #$id"
}

Write-Host "Setup Complete! Visit $($project.url) to view the roadmap."
