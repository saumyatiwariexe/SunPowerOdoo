import React from 'react'
import { Facts, Heading } from '../../app/records'
import { useAuth } from '../../app/AuthContext'
import { human } from '../../app/navigation'
export default function ProfilePage() {
  const { currentUser } = useAuth()
  return (
    <>
      <Heading title="Staff profile" />
      <Facts
        items={[
          ['Name', currentUser.name],
          ['Email', currentUser.email],
          ['Workspace role', human(currentUser.role)],
          ['Extra access', currentUser.additional_roles?.map(human).join(', ') || 'None'],
          ['Staff ID', currentUser.id],
          ['Phone', currentUser.phone],
        ]}
      />
    </>
  )
}
