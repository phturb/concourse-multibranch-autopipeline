req=$(curl "https://api.github.com/repos/phturb/concourse-multibranch-autopipeline/branches")
for i in "${req[@]}"
do
    echo $i
done
